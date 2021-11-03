/*
Data structure storing the userId of the most recent speakers.
The one that should be displayed as the active speaker is the
one with the highest score.

Implemented as a ring buffer.
*/
// Transcripts can be received up to every ~300 ms per active speaker
// so a buffer of 8 will be about 1.3 seconds for 2 active speakers.
const WEIGHTS = [5, 3, 2, 1, 1, 1, 1, 1];

class SpeakerRingBuffer {
  constructor(len) {
    if (len !== WEIGHTS.length) {
      throw "Doesn't support other buffer sizes";
    }

    this.arr = Array(len).fill(null);
    this.start = 0;
    this.len = len;
  }

  push = (val) => {
    this.arr[this.start] = val;
    this.start = (this.start + 1) % this.len;
  };

  /* Returns either a userId (string) or null (don't switch) */
  getActiveSpeaker = () => {
    let scores = {};
    for (let i = 0; i < this.len; i++) {
      const speaker = this.arr[(i + this.start) % this.len];
      if (speaker === null) {
        continue;
      }

      if (!(speaker in scores)) {
        scores[speaker] = 0;
      }
      scores[speaker] += WEIGHTS[this.len - i - 1];
    }

    let result = null;
    for (const speaker in scores) {
      if (result === null || scores[speaker] > scores[result]) {
        result = speaker;
      }
    }

    if (scores[result] > 10) {
      return result;
    } else {
      return null;
    }
  };
}

export default SpeakerRingBuffer;
