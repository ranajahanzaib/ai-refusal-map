# Evaluation protocol

Before training, create a versioned labeled benchmark with conversation-grouped train, validation and test splits. Check duplicate requests, repeated response templates and temporal leakage. Keep a final test split out of threshold selection. Record the source revision, annotation rubric/version, split seed and artifact hashes.

For binary or multiclass tasks, report per-class precision/recall/F1, macro and micro F1, balanced accuracy, MCC, confusion matrix and suitable PR/ROC AUC. For multilabel tasks, report per-label results, Hamming loss, Jaccard and exact match. For confidence estimates, report calibration plots, Brier score, expected calibration error and abstention coverage alongside threshold choice. Report language-specific results and sample sizes.

Classifier agreement is not ground-truth accuracy. No model training or evaluation has been executed by the current repository.
