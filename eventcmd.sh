#!/usr/bin/env bash

# this eventcmd.sh file was uncerimonously copied from the patiobar project by Kyle Johnson
# https://github.com/kylejohnson/Patiobar
# TODO: update to my own eventcmd

host="http://127.0.0.1"
port=3000
baseurl="${host}:${port}"


# Here be dragons! #
# (Don't change anything below) #

stationList="${HOME}/.config/pianobar/stations"
currentSong="${HOME}/.config/pianobar/nowplaying"

while read L; do
	k="`echo "$L" | cut -d '=' -f 1`"
	v="`echo "$L" | cut -d '=' -f 2`"
	export "$k=$v"
done < <(grep -e '^\(title\|artist\|album\|stationName\|songStationName\|pRet\|pRetStr\|wRet\|wRetStr\|songDuration\|songPlayed\|rating\|coverArt\|stationCount\|station[0-9]*\)=' /dev/stdin) # don't overwrite $1...




post () {
	url=${baseurl}${1}
	curl -s -XPOST $url >/dev/null 2>&1
}

clean () {
	query=$1
	clean=$(echo $query | sed 's/ /%20/g')
	post $clean
}

stationList () {
	if [ -f "$stationList" ]; then
		rm "$stationList"
	fi

	end=`expr $stationCount - 1`
	
	for i in $(eval echo "{0..$end}"); do
		sn=station${i}
		eval sn=\$$sn
		echo "${i}:${sn}" >> "$stationList"
	done
}


case "$1" in
	songstart)
		query="/start/?title=${title}&artist=${artist}&coverArt=${coverArt}&album=${album}&rating=${rating}&stationName=${stationName}"
		clean "$query"

		echo -n "${artist},,,${title},,,${album},,,${coverArt},,,${rating},,,${stationName}" > "$currentSong"

		stationList
		;;

#	songfinish)
#		;;

	songlove)
		query="/lovehate/?rating=${rating}"
		clean $query
		;;

#	songshelf)
#		;;

	songban)
		query="/lovehate/?rating=${rating}"
		clean $query
		;;

#	songbookmark)
#		;;

#	artistbookmark)
#		;;

esac

