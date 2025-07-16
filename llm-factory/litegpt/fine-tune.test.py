# 0) setup your dataset
# curl -L https://huggingface.co/datasets/ksaw008/finance_alpaca/resolve/main/finance_alpaca.json -o my_custom_dataset.json

## JSON EXAMPLE
## [
##   {
##     "instruction": "How do nonparametric tests handle missing data in hypothesis testing?",
##     "input": "",
##     "output": "Nonparametric tests are statistical tests that do not make any assumptions about the underlying distribution of the data. These tests are often used when the data does not meet the assumptions of parametric tests, such as normality or equal variances.\n\nWhen it comes to handling missing data in hypothesis testing using nonparametric tests, the following steps can be followed:\n\nStep 1: Identify the type of missing data\nDetermine whether the missing data is missing completely at random (MCAR), missing at random (MAR), or missing not at random (MNAR). MCAR means that the missingness is unrelated to the observed or unobserved values. MAR means that the missingness is related to the observed values but not the unobserved values. MNAR means that the missingness is related to the unobserved values.\n\nStep 2: Determine the appropriate method for handling missing data\nDepending on the type of missing data, different methods can be used. If the data is MCAR, it can be ignored and the analysis can proceed with the available data. If the data is MAR or MNAR, more sophisticated methods are required.\n\nStep 3: Imputation methods for MAR data\nIf the missing data is MAR, imputation methods can be used to estimate the missing values. Imputation involves replacing the missing values with estimated values based on the observed data. There are various imputation methods available, such as mean imputation, regression imputation, or multiple imputation. The choice of method depends on the nature of the data and the research question.\n\nStep 4: Sensitivity analysis for MNAR data\nIf the missing data is MNAR, it is more challenging to handle. In such cases, sensitivity analysis can be performed to assess the potential impact of the missing data on the results. This involves conducting the analysis multiple times, each time with a different assumption about the missing data mechanism. By comparing the results under different assumptions, the robustness of the conclusions can be evaluated.\n\nStep 5: Conduct the nonparametric test\nOnce the missing data has been handled using the appropriate method, the nonparametric test can be conducted. Examples of nonparametric tests include the Wilcoxon rank-sum test, Kruskal-Wallis test, and Mann-Whitney U test. These tests do not require assumptions about the underlying distribution of the data, making them suitable for situations with missing data.\n\nStep 6: Interpret the results\nFinally, the results of the nonparametric test can be interpreted in the context of the research question. The conclusions should be based on the available data, taking into account any imputations or assumptions made to handle the missing data.\n\nIt is important to note that handling missing data in hypothesis testing requires careful consideration and expertise. It is recommended to consult with a statistician or expert in the field to ensure appropriate methods are used."
##   }
## ]

# 1) Finetune a model (auto downloads weights)
litgpt finetune microsoft/phi-2 \
  --data JSON \
  --data.num_workers 32 \
  --data.json_path my_custom_dataset.json \
  --data.val_split_fraction 0.1 \
  --train.epochs 1 \
  --train.save_interval 5000 \
  --train.log_interval 10 \
  --train.global_batch_size 128 \
  --train.micro_batch_size 8 \
  --train.lr_warmup_steps 10 \
  --train.lr_warmup_fraction null \
  --train.max_tokens null \
  --train.max_steps null \
  --train.max_seq_length null \
  --train.tie_embeddings null \
  --train.max_norm null \
  --train.min_lr 6e-05 \
  --out_dir out/custom-model

# 2) Test the model
litgpt chat out/custom-model/final
