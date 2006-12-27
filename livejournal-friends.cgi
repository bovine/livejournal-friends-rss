#!/usr/bin/perl

require LWP::UserAgent;
require HTTP::Response;
require HTTP::Cookies;
require URI::URL;
require DateTime::Format::Mail;
require DateTime::Format::Strptime;
use Digest::MD5 qw(md5_hex);
use CGI qw/:standard/;
use CGI::Carp qw(fatalsToBrowser);
use strict;



my $username = param('username');
my $password = param('password');
die "missing or invalid username specified\n" if $username !~ m/^\w+$/;

if ($username eq 'bovineone' && !length($password) && open(STOREPASS, "/home/jlawson/.ljpassword")) {
    $password = <STOREPASS>;
    chomp($password);
    close(STOREPASS);
}

die "missing password\n" if !length($password);
my $ua = new LWP::UserAgent;
$ua->cookie_jar(HTTP::Cookies->new());



my $ljloginurl = "http://www.livejournal.com/mobile/login.bml";
my %loginfields = ( 'user' => $username,
		    'password' => $password );
my $response = $ua->post($ljloginurl, \%loginfields);

if (!$response->is_success && !$response->is_redirect) {
    print "Content-type: text/html\n\n";
    print $response->error_as_HTML;
    exit 0;
}

my $ljfriendsurl = "http://www.livejournal.com/mobile/friends.bml";
$response = $ua->get($ljfriendsurl);

if (!$response->is_success) {
    print "Content-type: text/html\n\n";
    print $response->error_as_HTML;
    exit 0;
}


my $html = $response->content;


$html =~ s|^.*?<h1>Friends Page</h1>||s
    or die "could not remove header\n";
$html =~ s|</body>.*$||s 
    or die "could not remove footer\n";


my $lastdate;
my @rssitems;
while ($html =~ m|<a href='(.*?)'><b>(.*?)</b></a>: <a href='(.*?)\?format=light'>(.*?)</a><br />|gis) {
    my ($loguserurl, $loguser, $loglink, $logsubject) = ($1, $2, $3, $4);

    # generate record.
    my %newitem = ( 'iid' => md5_hex("$loguser $logsubject"),
		    'title' => escapeHTML("$loguser -- $logsubject"),
		    'link' => escapeHTML($loglink)
		    );
    push(@rssitems, \%newitem);
}


print "Content-type: text/xml\n\n";
print "<rss version=\"2.0\">\n";
print "<channel><title>LiveJournal Friends for $username</title>\n";
print "<link>$ljfriendsurl</link>\n";
print "<description>LiveJournal Friends for $username</description>\n";
print "<language>en-us</language>\n";
print "<managingEditor>$username\@users.livejournal.com</managingEditor>\n";
print "<webMaster>$username\@users.livejournal.com</webMaster>\n";

foreach my $oneitem (@rssitems) {
    print '<item>';
    if (defined($oneitem->{'iid'})) {
	print '<guid isPermaLink="false">'. $oneitem->{'iid'} . '</guid>';
    } 
    if (defined($oneitem->{'title'})) {
	print '<title>' . $oneitem->{'title'} . '</title>';
    }
    if (defined($oneitem->{'link'})) {
	print "<link>" . $oneitem->{'link'} . "</link>";
    } else {
	print "<link>" . "about:blank" . "</link>";
    }
    if (defined($oneitem->{'pubdate'})) {
	print "<pubDate>" . $oneitem->{'pubdate'} . "</pubDate>";
    }
    print "</item>\n";
}

print "</channel></rss>\n";

exit 0;
