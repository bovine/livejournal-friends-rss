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

use Data::Dumper;

my $username = param('username');
my $password = '';

my $secret = param('secret');
my $maxposts = param('maxposts') || 15;
my $fulltext = param('fulltext') || 1;

#die "incorrect password" if $secret ne "sekret";
die "missing or invalid username specified\n" if $username !~ m/^\w+$/;
if ($username eq 'bovineone' && !length($password) && open(STOREPASS, "/home/jlawson/.ljpassword")) {
    $password = <STOREPASS>;
    chomp($password);
    close(STOREPASS);
}
die "missing password\n" if !length($password);

my $ua = new LWP::UserAgent;
$ua->cookie_jar(HTTP::Cookies->new());

my $strp = new DateTime::Format::Strptime(pattern => '%Y-%m-%d %T');
my $rfc822p = new DateTime::Format::Strptime(pattern => '%a, %d %b %Y %H:%M:%S %z');


my $ljfriendspage = "http://$username.livejournal.com/friends";
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

$html =~ s|^.*?>Friends Page</div>||s
    or die "could not remove header\n";
$html =~ s|^.*?Previous 50</a></div>||s;
$html =~ s|</body>.*$||s 
    or die "could not remove footer\n";

my $lastdate;
my $numposts = 0;
my @rssitems;

while (($numposts++ < $maxposts) and $html =~ m|<a href='(.*?)'><b>(.*?)</b></a>: <a href='(.*?)\?format=light'>(.*?)</a>|gis) {
    my ($loguserurl, $loguser, $loglink, $logsubject) = ($1, $2, $3, $4);

    # community post html strip
    $loguser =~ s|</b></a> in <a href='.*?'><b>(.*?)| in $1|;

    my $itemhtml = "";
    my $pubdate = "";
    if ($fulltext) {
        my $sanelink = escapeHTML($loglink)."?format=light";
        my $itemresponse = $ua->get($sanelink);
        if (!$itemresponse->is_success) {
            print "Content-type: text/html\n\n";
            print $response->error_as_HTML;
            exit 0;
        }
        $itemhtml = $itemresponse->content;

#print $itemhtml;

        $itemhtml =~ m|<a href=".*?">(\d+)</a>-<a href=".*?">(\d+)</a>-<a href=".*?">(\d+)</a> (\d+):(\d+):(\d+)|gis
	    or die "could not isolate datestamp\n";
        my $ljtime = "$1-$2-$3 $4:$5:$6";
#print "$ljtime\n";
        my $dt = $strp->parse_datetime($ljtime);
#print Dumper $dt;
        $pubdate = $rfc822p->format_datetime($dt);
       

        $itemhtml =~ s|^.*?</blockquote>.*?<div>||s
            or die "could not remove item header\n";
        $itemhtml =~ s|<div id="comments".*$||s
            or die "could not remove item footer\n";
        #strip title, if present
        $itemhtml =~ s|<font face='Arial,Helvetica' size='\+1'><i><b>.*</b></i></font><br />||s;
    }

    # generate record.
    my %newitem = ( 'title' => escapeHTML($logsubject),
                    'author' => escapeHTML($loguser),
                    'link' => escapeHTML($loglink),
                    'pubdate' => $pubdate,
                    'content' => $itemhtml,
                  );
    push(@rssitems, \%newitem);

#print "$loguserurl, $loguser, $pubdate, $loglink, $logsubject\n";

}

my $nowtime = $rfc822p->format_datetime(DateTime->now);

print "Content-type: text/xml\n\n";
print "<rss version=\"2.0\">\n";
print "<channel>\n<title>LiveJournal Friends for $username</title>\n";
print "<link>$ljfriendspage</link>\n";
print "<description>LiveJournal Friends for $username</description>\n";
print "<language>en-us</language>\n";
print "<managingEditor>$username\@users.livejournal.com</managingEditor>\n";
print "<webMaster>$username\@users.livejournal.com</webMaster>\n";
print "<pubDate>$nowtime</pubDate>\n<lastBuildDate>$nowtime</lastBuildDate>\n";

foreach my $oneitem (@rssitems) {
    print "<item>\n";
    if (defined($oneitem->{'title'})) {
	print "\t<title>" . $oneitem->{'author'} . " -- " . $oneitem->{'title'} . "</title>\n";
    }
    if (defined($oneitem->{'author'})) {
        print "\t<author><name>" . $oneitem->{'author'} . "</name></author>\n";
    }
    if (defined($oneitem->{'link'})) {
	print "\t<guid isPermaLink=\"true\">". $oneitem->{'link'} . "</guid>\n";
	print "\t<link>" . $oneitem->{'link'} . "</link>\n";
    } else {
	print "\t<link>" . "about:blank" . "</link>\n";
    }
    if (defined($oneitem->{'pubdate'})) {
	print "\t<pubDate>" . $oneitem->{'pubdate'} . "</pubDate>\n";
    }
    if (defined($oneitem->{'content'})) {
        print "\t<description><![CDATA[" . $oneitem->{'content'} . "]]></description>\n";
    }

    print "</item>\n";
}

print "</channel></rss>\n";

exit 0;
