#!/bin/bash

###########################################################################
# Sample call:
#   % ./call_hmm_segmenter.sh [NUM_SEGMENTS] [DATAFILE] [RESTARTS]
# Cuts [DATAFILE] into [NUM_SEGMENTS] segments. (with [RESTARTS] number of random restarts; default value = 20)
#
# NOTE: Needs CARMEL installed at '/usr/local/bin/carmel'
# Format of the [DATAFILE]
# ---
# <newline>
# Arkady Kevin Kevin Kevin Arkady Arkady Kevin Arkady Kevin Arkady Kevin Ajay Arkady Kevin Kevin Arkady Kevin Kevin Arkady Kevin yiqi Arkady scot Ajay Arkady Kevin Kevin Kevin chris yiqi yiqi scot yiqi chris scot Kevin Arkady yiqi Kevin yiqi Kevin chris Kevin Kevin Kevin Kevin scot Kevin scot Kevin scot Kevin Kevin Kevin Yiqi Yiqi chris Yiqi chris Yiqi boliang Kevin Ajay chris Yiqi Ajay chris Yiqi boliang boliang boliang chris boliang chris chris Kevin Kevin Kevin Kevin Kevin Kevin Kevin Yiqi Kevin Kevin Yiqi Yiqi Kevin Kevin Kevin chris Ajay Kevin chris Ajay Kevin chris Ajay chris Ajay Kevin Kevin Kevin Kevin Yiqi Yiqi scot scot Ajay Kevin Ajay Kevin Kevin Ajay Kevin Kevin scot scot Kevin
#--
# each word is a speaker's utterance line in the transcript
#----
# How:
# Solves segmentation as an unsupervised labeling problem, where
#   labels are seg1, seg2, ... segn.
# Takes observed string S as input.
# Noisy channel model to "explain" S:
#   Generate label sequence of the form seg1+ seg2+ ... segn+
#   Generate words from labels via P(word | label)
# Runs Carmel HMM to estimate P(word | label), maximizing P(S)
# Then run Viterbi to extract best path (best labeling of S).
# Many random restarts to search for optimal P(word | label).
# NOTE: search is hard, may not find same result every time it is run!

TMP=$1
data_file="${TMP}/speaker_info.data"
split=$2 # 6
restarts=20 # value from KK
log_file="${TMP}/hmm_segmenter.log"
result_viz="${TMP}/hmm_split.newline"
speaker_viz="${TMP}/speaker_info.newline"
result_file="${TMP}/hmm_split"

CARMEL=/usr/local/bin/carmel
SEGS=${split}
DATA=${data_file}
RESTARTS=${restarts}

rm -f $DATA.wfsa $DATA.wfst

echo $SEGS+1 | bc >$DATA.wfsa
for i in `seq $SEGS`
do
  echo '('$i' ('$i' *e* seg'$i'))' >>$DATA.wfsa
  K=`echo $i'+1' | bc`
  echo '('$i' ('$K' *e* seg'$i'))' >>$DATA.wfsa
done

echo 0 >$DATA.wfst
for i in `seq $SEGS`
do
  for j in `cat $DATA | tr ' ' '\n' | sort | uniq`
  do
    echo '(0 (0 seg'$i' '$j'))' >>$DATA.wfst
  done
done

# Run HMM segmenter on data

$CARMEL -X 0.99999 -HJ --train-cascade -! $RESTARTS $DATA $DATA.wfsa $DATA.wfst >> ${log_file} 2>&1
$CARMEL -HJ --project-right --project-identity-fsa $DATA.wfsa.trained >$DATA.wfsa.trained.noe 2>>${log_file}
$CARMEL -briIEQk 1 $DATA.wfsa.trained.noe $DATA.wfst.trained $DATA | tr ' ' '\012' | egrep '(seg|topic)' >$DATA.viterbi
#paste ../speakers/0326.who.all.txt ../segments/0326.seg.txt >data.human
#cat $DATA.wfst.trained | egrep -v '(e.-|e-)' | tr -d '")' | awk '{printf("%s %12s %6.2f\n",$3,$4,$5)}' | sort -k1,1 -k3nr
echo '' >> ${log_file}
cat $DATA.viterbi | tr -d '"' | tr '\n' ' ' >> ${log_file}
cat $DATA.viterbi | uniq -c
echo ''  >> ${log_file}

result=`cat ${log_file} | tail -n1`
echo -e "${result}" | tr ' ' '\n' | grep -v ^$ > ${result_viz}
echo ${result} > ${result_file}
