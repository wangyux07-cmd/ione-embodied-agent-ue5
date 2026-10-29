# Ione LoRA trial

Build a Colab notebook and upload archive from an approved SFT bundle:

```powershell
python Tools/package_ione_colab.py --bundle PATH_TO_FROZEN_BUNDLE --output NEW_OUTPUT_DIRECTORY
```

The bundle contains `manifest.json`, `sft_train_canonical.jsonl`, `sft_dev_canonical.jsonl`, `sft_train.jsonl` and `sft_dev.jsonl`. The manifest records `status: approved_frozen`, `counts.SFT_train`, `counts.SFT_dev`, `heldout_sha256` and SHA-256 values in `files_sha256`. Canonical records follow `ione_data_pipeline.py`; exports use TRL conversational prompt/completion format. Keep data and generated results in a private local directory such as `Saved/`.

Upload the generated notebook to [Colab](https://colab.research.google.com/), select a free GPU runtime and run all cells. At the upload prompt, select the matching `ione_colab_bundle.zip`. The notebook verifies its hash, installs `requirements-m6-colab.txt` and keeps Colab's CUDA-enabled PyTorch.

The trial runs Qwen3-0.6B for three optimizer steps on independent mechanics fixtures, saves and reloads its LoRA adapter, then runs one Qwen3-1.7B epoch on the approved train split and evaluates dev loss. Both Hugging Face revisions are pinned in `train_ione_sft.py`. Loss covers assistant completions and their stop token. Base parameters stay frozen; LoRA targets Q/V with rank 8 and alpha 16.

Download `ione_results.zip` before disconnecting the runtime. It contains adapters, optimizer checkpoints, configuration, loss logs, GPU details, environment versions and reload checks. Training failure also triggers a log download. Compare Base/SFT answers under a matched inference protocol to evaluate NPC quality.

Run normal regression tests with `python -m pytest -q`. For the optional integration check, install `requirements-m6-preflight.txt` in a separate environment and run:

```powershell
python Tests/smoke_sft_trainer_cpu.py --tokenizer LOCAL_QWEN_TOKENIZER --output NEW_TEST_OUTPUT_DIRECTORY
```

This integration check uses a tiny random CPU model and exercises TRL training, evaluation, adapter save and reload.
