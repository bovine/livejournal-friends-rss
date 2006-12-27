#!/usr/bin/perl

require LWP::UserAgent;
require HTTP::Response;
require URI::URL;
require DateTime::Format::Mail;
require DateTime::Format::Strptime;
use Digest::MD5 qw(md5_hex);
use CGI qw/:standard/;
use CGI::Carp qw(fatalsToBrowser);
use constant MAXITEMS => 25;
use strict;


sub striphtml ($) {
    my $html = shift;
    $html =~ s/<[^>]+>/ /gs;
    $html =~ s/\&\w+\;/?/gs;
    $html =~ s/\&\#\d+\;/?/gs;
    $html =~ s/^\s+//s;
    $html =~ s/\s+$//s;
    return $html;
}



my $username = param('username');
die "missing or invalid username specified\n" if $username !~ m/^\w+$/;
my $ljurl = sprintf("http://www.livejournal.com/users/%s/friends", $username);


my $ua = new LWP::UserAgent;
my $request = new HTTP::Request('GET', $ljurl);
my $response = $ua->request($request);
if (!$response->is_success) {
    print "Content-type: text/html\n\n";
    print $response->error_as_HTML;
    exit 0;
}



my $html = $response->content;
$html =~ s|^.*?Below are the most recent.*?<table[^>]+>||s 
    or die "could not remove header\n";
$html =~ s|</table>\s+?<center>[^\n]+?Previous\s+\d+.*$||s 
    or die "could not remove footer\n";


my $lastdate;
my @rssitems;
while ($html =~ m|<tr>(.*?)</tr>|gis) {
    my @columns = ($1 =~ m|<td[^>]*>(.*?)</td>|gis);
    
    my %newitem;
    if (scalar(@columns) == 1) {
	# parse date stamp.
	my $newdatetxt = striphtml($columns[0]);
	next if $newdatetxt !~ m/\S+/;
	next if $newdatetxt !~ m/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)/i;
	my $tmpdatetxt = $newdatetxt;
	$tmpdatetxt =~ s/(\d)(st|nd|rd|th),/$1,/s;
	my $Strp = new DateTime::Format::Strptime('pattern' => '%A, %B %e, %Y', 'time_zone' => 'US/Central');
	my $dateobj = $Strp->parse_datetime($tmpdatetxt) or next;
	$lastdate = $dateobj;

	# generate record.
	$newitem{'iid'} = md5_hex($newdatetxt);
	$newitem{'title'} = "*** $newdatetxt ***" ;
	$newitem{'pubdate'} =  DateTime::Format::Mail->format_datetime($dateobj);
	$newitem{'link'} = "javascript:void('$newdatetxt')";
    } elsif (scalar(@columns) == 3) {
	my ($loguser, $logtime, $logtext) = map { striphtml($_) } @columns;

	# compute full timestamp.
	next if ($logtime !~ m/^(\d{1,2}):(\d{1,2})([ap]m?)?$/);
	my ($hour, $minute) = ($1, $2);
	$hour %= 12;
	$hour += 12 if $3 =~ m/^p/i;
	$lastdate->set('hour' => $hour);
	$lastdate->set('minute' => $minute);

	# sanitize username
	if ($loguser =~ m/(\S+)\n\[.*?\]/) {
	    $loguser = $1;      # community posting, so keep only the community name.
	} elsif ($loguser !~ m/^\S+$/) {
	    next;
	}

	# sanitize summary.
	if (length($logtext) > 80) {
	    $logtext = substr($logtext, 0, 80) . "...";
	}

	# sanitize url to posting.
	my ($loglink) = ($columns[2] =~ m{<a href=\"(http://www.livejournal.com/(?:users|community)/$loguser/\d+\.html)}is);
	
	# generate record.
	$newitem{'iid'} = md5_hex("$loguser $lastdate $logtime");
	$newitem{'title'} = escapeHTML("($logtime) $loguser -- $logtext");
	$newitem{'link'} = escapeHTML($loglink);
	$newitem{'pubdate'} = DateTime::Format::Mail->format_datetime($lastdate);
    } else {
	#print STDERR "got " . scalar(@columns)  . " columns\n";
	next;
    }
    push(@rssitems, \%newitem);
}




if (param('mode') eq 'rss') {
    print "Content-type: text/xml\n\n";
    print "<rss version=\"2.0\">\n";
    print "<channel><title>LiveJournal Friends for $username</title>\n";
    print "<link>$ljurl</link>\n";
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


} else {
    print "Content-type: text/xml\n\n";
    print "<klipfood>\n";

    foreach my $oneitem (@rssitems) {
	if (defined($oneitem->{'iid'})) {
	    print '<item iid="' . $oneitem->{'iid'} . '">';
	} else {
	    print '<item>';
	}
	if (defined($oneitem->{'title'})) {
	    print '<title>' . $oneitem->{'title'} . '</title>';
	}
	if (defined($oneitem->{'link'})) {
	    print "<link>" . $oneitem->{'link'} . "</link>";
	}
	print "</item>\n";
    }

    print "</klipfood>\n";
}

exit 0;
