# Evaluation

## Setup

- Download the test sets from [here](https://drive.google.com/file/d/1om_WWz5zVy714j9COFSlE8DB_1ti5V4e/view?usp=sharing).
- Extract the test sets into this directory: `tar -xvf data.tar.gz`
- Run the `evaluate.py` script (from `backend`). To see the available arguments, run "python src/services/evaluation/evaluate.py --help"
- The default config that will be used is at configs/default.json, you can update specific values only specifying the keys you want to change, as in configs/didi.json

## Visual Comparison

For speech translation systems' output, we provide a script to do visual comparison. You could run following command:

```
python src/services/evaluation/compare.py  \
--systems system1_output/st/ system2_output/st/  \
--output_dir XXX/xx/ \
--test_set dwc2-en-zh
```

And you can get row-wise comparison between outputs of system 1 and system 2:

```
SAID:  Same pronunciation, but one character wrong.

System 1:  same pronunciation but at what time characters

System 2:  same pronunciation but one character wrong

REF:  相同的读音，不过错了一个字。

System 1:  发音相同，但在什么时候字符。

System 2:  同一个发音，但一个字符错误。
```
