# Summarization module

- Takes the history of utterances as input and generates a keyphrase-based extractive summary.
- Dependencies
  - [carmel](https://github.com/graehl/carmel): segments the history into >1 topics using speaker turn information
  - [yake](https://github.com/LIAAD/yake): extracts keyphrases in an unsupervised manner.

## Carmel

- Assumes carmel is present at `/usr/local/bin/carmel`
- To install `carmel`, follow the [installation instructions](https://github.com/graehl/carmel/blob/master/README.md).
- `carmel` is invoked through a `bash` script.

## Notes

- A segment can be 15 minutes long. Every 15 minutes adds one additional segment as argument to `carmel`. A meeting consists of a maximum of 6 segments. These parameters are configurable.
- The segmenter works reasonably well on multi-party party meetings. But in 2-person meetings, segmentation is not very effective (as it is based on speaker turn information).
- Extracts a context of 3 words to the left and right around the keyphrase extracted by `yake`. Currently, extracts 3 such keyphase snippets from a meeting segment (configurable).
- Displays the relative length of each meeting segment (ratio number of words spoken in that segment and the whole meeting). Additionally, lists the main speakers in that segment (in decreasing order of words spoken).
- Works on English, Spanish, Chinese and Portuguese meeting transcripts.
