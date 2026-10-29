# Ione LoRA trial

Build a Colab notebook and upload archive from an approved SFT bundle:

```powershell
python Tools/package_ione_colab.py --bundle PATH_TO_FROZEN_BUNDLE --output NEW_OUTPUT_DIRECTORY
```

Add `--with-dev-eval` to run matched Base/SFT development inference after the pilot's checkpoint reload, then download training and evaluation results together. The frozen test set stays outside this pilot batch.

The bundle contains `manifest.json`, `sft_train_canonical.jsonl`, `sft_dev_canonical.jsonl`, `sft_train.jsonl` and `sft_dev.jsonl`. The manifest records `status: approved_frozen`, `counts.SFT_train`, `counts.SFT_dev`, `heldout_sha256` and SHA-256 values in `files_sha256`. Canonical records follow `ione_data_pipeline.py`; exports use TRL conversational prompt/completion format. Keep data and generated results in a private local directory such as `Saved/`.

Upload the generated notebook to [Colab](https://colab.research.google.com/), select a free GPU runtime and run all cells. At the upload prompt, select the matching `ione_colab_bundle.zip`. The notebook verifies its hash, installs `requirements-m6-colab.txt` and keeps Colab's CUDA-enabled PyTorch.

The trial runs Qwen3-0.6B for three optimizer steps on independent mechanics fixtures, saves and reloads its LoRA adapter, then runs one Qwen3-1.7B epoch on the approved train split and evaluates dev loss. Both Hugging Face revisions are pinned in `train_ione_sft.py`. Loss covers assistant completions and their stop token. Base parameters stay frozen; LoRA targets Q/V with rank 8 and alpha 16.

GPUs with native BF16 use BF16. On GPUs such as T4, the smoke uses FP16 and the 1.7B pilot uses FP32. Logs distinguish attempted, skipped and successful optimizer steps; non-finite loss or gradient norms stop the run. To reuse a completed smoke for the same bundle, add `--smoke-result PATH_TO_SMOKE_RESULT_JSON` when building the package.

Download `ione_results.zip` before disconnecting the runtime. It contains adapters, optimizer checkpoints, configuration, loss logs, GPU details, environment versions and reload checks. Training failure also triggers a log download. Compare Base/SFT answers under a matched inference protocol to evaluate NPC quality.

Run normal regression tests with `python -m pytest -q`. For the optional integration check, install `requirements-m6-preflight.txt` in a separate environment and run:

```powershell
python Tests/smoke_sft_trainer_cpu.py --tokenizer LOCAL_QWEN_TOKENIZER --output NEW_TEST_OUTPUT_DIRECTORY
```

This integration check uses a tiny random CPU model and exercises TRL training, evaluation, adapter save and reload.

For a paired development diagnostic, run `python Tools/eval_ione_adapter.py --packet EVAL_PACKET --output NEW_OUTPUT_DIRECTORY` on a CUDA GPU. The packet contains `training_result.json`, `sft_dev_canonical.jsonl`, the saved `adapter/adapter_config.json` and `adapter/adapter_model.safetensors`, plus an `eval_manifest.json` with their SHA-256 values in `files_sha256`. It generates Base/SFT replies with the same pinned FP32 model, alternating pair order and toggling its adapter. Outputs include target-only dev loss, raw replies, truncation and generation timing. Quality labels remain pending review. The diagnostic performs no training or game actions.

For DPO, use approved canonical preference records and a manifest with `pairs`, `approval_reference` and their SHA-256 in `files`. Approval for batch use and individual annotation provenance are recorded separately. Run on a free CUDA GPU:

```powershell
python Tools/train_ione_dpo.py --data PREFERENCES_JSONL --manifest APPROVAL_MANIFEST --sft-adapter SFT_ADAPTER_DIRECTORY --output NEW_DPO_DIRECTORY
python Tools/eval_ione_dpo.py --packet FROZEN_EVAL_PACKET --dpo-run NEW_DPO_DIRECTORY --output NEW_COMPARISON_DIRECTORY
```

DPO trains one FP32 epoch with learning rate `1e-5` and beta `0.1`. Policy and reference start from the same SFT adapter and share a frozen base. The reference stays fixed, and only policy LoRA weights enter the optimizer. Non-thinking prompts are explicit; sequences exceeding 1536 tokens stop before training. The saved policy is independently reloaded before evaluation.

The evaluation packet contains the frozen cases, approval manifest, Character Bible, SFT training result and adapter, with file hashes in `packet_manifest.json`. SFT/DPO inference alternates pair order on the same FP32 model and records raw replies and timing. Human preference and semantic quality ratings are collected separately.

The optional CPU integration test checks two actual DPO updates, frozen reference/base, policy-only optimizer, independent reload and named-adapter evaluation on a tiny random model:

```powershell
python Tests/smoke_dpo_trainer_cpu.py --tokenizer LOCAL_QWEN_TOKENIZER --output NEW_TEST_OUTPUT_DIRECTORY
```

The optional runtime worker loads one FP32 base and the verified SFT/DPO adapters. In the training Python environment, start it with the saved result files and adapter directories:

```powershell
python Tools/serve_ione_hf.py --sft-result SFT_RESULT_JSON --dpo-result DPO_RESULT_JSON --sft-adapter SFT_ADAPTER_DIRECTORY --dpo-adapter DPO_ADAPTER_DIRECTORY --device cuda
```

Weights load from the local Hugging Face cache. Add `--allow-download` to download the pinned public base. CPU inference requires explicit `--device cpu`. The worker binds to `127.0.0.1:8770`, serializes shared-adapter inference and records generation time, first-token time, queue time and token counts.

Start the game bridge in a separate terminal with `python Tools/serve_ione_agent.py --dialogue-model dpo`; choose `base` or `sft` for the other variants. The default is `authored`. ToolGate commits validated actions before optional dialogue generation. The existing fact-anchor gate accepts or replaces model prose. A newer turn cancels publication of an older reply while preserving any action already committed. Raw output and fallback reasons stay in the local turn log.

For a matched service comparison, run:

```powershell
python Tools/benchmark_ione_runtime.py --output NEW_OUTPUT_DIRECTORY --repeats 3
```

This sends 36 measured requests per variant after separate warmups, using fixed structured story actions and a route fixture. JSONL and CSV outputs separate model timing, Python wall time, accepted dialogue and fallbacks. UE drawing and natural-language router timing are measured separately.

`Tools/package_ione_runtime_colab.py` accepts the same four artifact arguments and `--output NEW_DIRECTORY` to produce a private free-Colab notebook and upload ZIP. It runs the comparison with existing weights and performs zero training updates. The optional CPU integration check is `python Tests/smoke_hf_runtime_cpu.py --tokenizer LOCAL_QWEN_TOKENIZER --output NEW_DIRECTORY`; it uses tiny random weights to test the HTTP, adapter-selection and game-state paths.
