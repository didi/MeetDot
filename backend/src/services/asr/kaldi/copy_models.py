import argparse
import json
import shutil
from pathlib import Path

from utils import deep_update

default_file_paths = {
    "am_final_mdl": "final.mdl",
    "am_tree": "tree",
    "conf_mfcc": "conf/mfcc.conf",
    "model_conf": "models/en-US/conf/model.conf",
    "graph_hclg": "graph_pp/HCLG.fst",
    "graph_disambig": "graph_pp/disambig_tid.int",
    "graph_phones": "graph_pp/phones",
    "graph_words": "graph_pp/words.txt",
    "graph_phones_txt": "graph_pp/phones.txt",
    "ivector_final_dubm": "ivector_extractor/final.dubm",
    "ivector_final_mat": "ivector_extractor/final.mat",
    "ivector_online_cmvn": "ivector_extractor/online_cmvn.conf",
    "ivector_final_ie": "ivector_extractor/final.ie",
    "ivector_global_cmvn": "ivector_extractor/global_cmvn.stats",
    "ivector_splice_opts": "ivector_extractor/splice_opts",
}


def copy_models(input_dir, output_dir, file_paths_json=None):
    output_dir.mkdir(parents=True, exist_ok=True)

    file_paths = default_file_paths

    if file_paths_json is not None:
        with open(file_paths_json) as f:
            file_paths = deep_update(file_paths, json.read(f))

    for subdir in ("am", "conf", "graph", "ivector"):
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Copy AM files
    am_dir = output_dir / "am"
    shutil.copy(input_dir / file_paths["am_final_mdl"], am_dir)
    shutil.copy(input_dir / file_paths["am_tree"], am_dir)

    # Copy conf
    conf_dir = output_dir / "conf"
    shutil.copy(input_dir / file_paths["conf_mfcc"], conf_dir)
    shutil.copy(Path(__file__).parent / file_paths["model_conf"], conf_dir)

    # Copy graph
    graph_dir = output_dir / "graph"
    shutil.copy(input_dir / file_paths["graph_hclg"], graph_dir)
    shutil.copy(input_dir / file_paths["graph_disambig"], graph_dir)
    shutil.copy(input_dir / file_paths["graph_words"], graph_dir)
    shutil.copy(input_dir / file_paths["graph_phones_txt"], graph_dir)

    if (graph_dir / "phones").exists():
        shutil.rmtree(graph_dir / "phones")
    shutil.copytree(input_dir / file_paths["graph_phones"], graph_dir / "phones")

    # Copy ivectory
    ivector_dir = output_dir / "ivector"
    shutil.copy(input_dir / file_paths["ivector_final_dubm"], ivector_dir)
    shutil.copy(input_dir / file_paths["ivector_final_mat"], ivector_dir)
    shutil.copy(input_dir / file_paths["ivector_online_cmvn"], ivector_dir)
    shutil.copy(input_dir / file_paths["ivector_final_ie"], ivector_dir)
    shutil.copy(input_dir / file_paths["ivector_global_cmvn"], ivector_dir)
    with open(input_dir / file_paths["ivector_splice_opts"]) as f, open(
        ivector_dir / "splice.conf", "w"
    ) as g:
        g.write(f.read().replace(" --", "\n--"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", "-i", type=Path)
    parser.add_argument("--output_dir", "-o", type=Path)
    parser.add_argument("--file_paths", type=Path, default=None)
    args = parser.parse_args()

    copy_models(args.input_dir, args.output_dir, args.file_paths)
