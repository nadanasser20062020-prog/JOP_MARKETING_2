'use strict';

const modelArtifact = require('../../ml/models/role_title_nb_v1.json');

function round(value, digits = 6) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function prepareModel(artifact) {
  if (artifact.modelId !== 'positive_skill_naive_bayes_observed_title_v1'
      || artifact.modelVersion !== 1
      || !Array.isArray(artifact.vocabulary)
      || !Array.isArray(artifact.classes)
      || !Number.isInteger(artifact.trainingRecordCount)
      || artifact.trainingRecordCount <= 0) {
    throw new Error('The bundled role-title model artifact is invalid.');
  }

  const alpha = Number(artifact.hyperparameters?.alpha);
  const priorWeight = Number(artifact.hyperparameters?.priorWeight);
  if (!(alpha > 0) || !Number.isFinite(priorWeight)) {
    throw new Error('The bundled role-title model hyperparameters are invalid.');
  }

  const skillIndex = new Map(artifact.vocabulary.map((skill, index) => [skill.skillId, index]));
  const classes = artifact.classes.map((item) => {
    const recordCount = Number(item.trainingRecordCount);
    const denominator = recordCount + 2 * alpha;
    const counts = new Map(item.skillDocumentCounts);
    const defaultSkillLogProbability = Math.log(alpha / denominator);
    const skillLogProbabilities = new Float64Array(artifact.vocabulary.length);
    skillLogProbabilities.fill(defaultSkillLogProbability);
    for (const [index, count] of item.skillDocumentCounts) {
      if (!Number.isInteger(index) || index < 0 || index >= skillLogProbabilities.length
          || !Number.isInteger(count) || count < 0 || count > recordCount) {
        throw new Error('The bundled role-title model contains an invalid skill count.');
      }
      skillLogProbabilities[index] = Math.log((count + alpha) / denominator);
    }
    return {
      roleId: item.roleId,
      displayTitle: item.displayTitle,
      trainingRecordCount: recordCount,
      skillCounts: counts,
      logPrior: priorWeight * Math.log(recordCount / artifact.trainingRecordCount),
      defaultSkillLogProbability,
      skillLogProbabilities,
    };
  });

  const backgroundCounts = artifact.backgroundSkillDocumentCounts;
  if (!Array.isArray(backgroundCounts) || backgroundCounts.length !== artifact.vocabulary.length) {
    throw new Error('The bundled role-title model background counts are invalid.');
  }

  return {
    artifact,
    alpha,
    priorWeight,
    skillIndex,
    classes,
    backgroundCounts,
  };
}

const preparedModel = prepareModel(modelArtifact);

function getModelStatus() {
  const test = modelArtifact.evaluation?.heldOutTest || {};
  const selectedPriorWeight = modelArtifact.evaluation?.selectedPriorWeight;
  const validation = modelArtifact.evaluation?.validationByPriorWeight?.[String(selectedPriorWeight)] || {};
  return {
    runtime: { implementation: 'Node.js', separateMlServer: false },
    productionModels: [],
    servedModels: [{
      id: modelArtifact.modelId,
      version: modelArtifact.modelVersion,
      status: 'limited_scope_review_only_not_production_approved',
      task: modelArtifact.task,
      modelFamily: modelArtifact.modelFamily,
      trainedModel: true,
      inferenceRuntime: 'Node.js',
      trainingRuntime: 'Python offline only',
      sourceArchiveRunId: modelArtifact.sourceArchiveRunId,
      trainingRecords: modelArtifact.trainingRecordCount,
      trainedTitleClasses: modelArtifact.coverage.trainedTitleClasses,
      minimumTrainingRecordsPerTitle: modelArtifact.hyperparameters.minimumTrainingRecordsPerTitle,
      priorWeight: modelArtifact.hyperparameters.priorWeight,
      trainingCoveragePercent: modelArtifact.coverage.trainingCoveragePercent,
      testCoveragePercent: modelArtifact.coverage.testCoveragePercent,
      validation: {
        evaluatedRecords: validation.evaluatedRecords,
        top1Accuracy: validation.top1Accuracy,
        priorOnlyTop1Accuracy: validation.priorOnlyTop1Accuracy,
        top5Accuracy: validation.top5Accuracy,
        priorOnlyTop5Accuracy: validation.priorOnlyTop5Accuracy,
        selectionCriterion: modelArtifact.evaluation?.selectionCriterion,
      },
      heldOutTest: {
        evaluatedRecords: test.evaluatedRecords,
        top1Accuracy: test.top1Accuracy,
        priorOnlyTop1Accuracy: test.priorOnlyTop1Accuracy,
        top5Accuracy: test.top5Accuracy,
        priorOnlyTop5Accuracy: test.priorOnlyTop5Accuracy,
      },
    }],
    availableAlgorithms: [{
      id: 'positive_skill_naive_bayes_observed_title_v1',
      status: 'trained_model_available_with_caveats',
      kind: 'positive_evidence_bernoulli_naive_bayes',
      trainedModel: true,
      explanation: 'Ranks sufficiently supported exact normalized title strings using the observed presence of reviewed skills; missing input skills are not treated as negative evidence.',
    }, {
      id: 'jaccard_skill_overlap',
      status: 'baseline_available',
      kind: 'deterministic_similarity',
      trainedModel: false,
      explanation: 'Explainable set overlap between user-selected reviewed skills and observed role skill profiles.',
    }],
    offlineExperiments: [{
      id: 'skill_profile_clustering',
      status: 'exploratory_report_only',
      serving: false,
      reason: 'No saved clustering model or human-approved stable user-facing cluster labels were approved.',
    }],
    disabledFeatures: [
      { id: 'salary_regression', reason: 'Currency, pay-period, target provenance, and sample-quality gates are not met.' },
      { id: 'job_family_classification', reason: 'No reviewed consistent job-family taxonomy or human-labelled training set exists.' },
      { id: 'active_listing_prediction', reason: 'Listing activity is unknown_not_verified; no verified outcomes or observation windows.' },
    ],
    warning: 'The Naive Bayes output is a relative, uncalibrated score over supported title strings in the collected sample; it is not a hiring probability, job-availability estimate, qualification judgment, or stable occupational classification.',
  };
}

function predictRoleTitles(recognizedSkills, limit = 5) {
  const modeledSkills = [];
  const unmodeledSkills = [];
  const seen = new Set();
  for (const skill of recognizedSkills) {
    if (seen.has(skill.skillId)) continue;
    seen.add(skill.skillId);
    const index = preparedModel.skillIndex.get(skill.skillId);
    if (index === undefined) {
      unmodeledSkills.push(skill);
    } else {
      modeledSkills.push({ ...skill, index });
    }
  }

  if (modeledSkills.length < 2) {
    const error = new Error('At least two submitted skills must be represented in the trained model.');
    error.code = 'INSUFFICIENT_MODEL_SKILLS';
    error.statusCode = 422;
    error.safeDetails = {
      recognizedModeledSkillCount: modeledSkills.length,
      minimumModeledSkillCount: 2,
      unmodeledSkills: unmodeledSkills.map(({ skillId, name }) => ({ skillId, name })),
    };
    throw error;
  }

  const scored = preparedModel.classes.map((item) => {
    let logScore = item.logPrior;
    for (const skill of modeledSkills) {
      logScore += item.skillLogProbabilities[skill.index] ?? item.defaultSkillLogProbability;
    }
    return { item, logScore };
  }).sort((left, right) => right.logScore - left.logScore
    || left.item.roleId.localeCompare(right.item.roleId));

  const maximumLogScore = scored[0]?.logScore ?? 0;
  const normalizer = scored.reduce((sum, item) => sum + Math.exp(item.logScore - maximumLogScore), 0);
  const vocabulary = modelArtifact.vocabulary;
  const alpha = preparedModel.alpha;
  const modelRecordCount = modelArtifact.trainingRecordCount;
  const validation = modelArtifact.evaluation.validationByPriorWeight[
    String(modelArtifact.evaluation.selectedPriorWeight)
  ];
  const predictions = scored.slice(0, limit).map(({ item, logScore }) => {
    const skillSignals = modeledSkills.map((skill) => {
      const classCount = item.skillCounts.get(skill.index) || 0;
      const classRate = (classCount + alpha) / (item.trainingRecordCount + 2 * alpha);
      const corpusCount = preparedModel.backgroundCounts[skill.index] || 0;
      const corpusRate = (corpusCount + alpha) / (modelRecordCount + 2 * alpha);
      return {
        skillId: skill.skillId,
        name: skill.name,
        titleTrainingRecordsWithSkill: classCount,
        titleSkillPresenceRate: round(classRate),
        modelSkillPresenceRate: round(corpusRate),
        logEvidenceRatio: round(Math.log(classRate / corpusRate)),
      };
    }).sort((left, right) => right.logEvidenceRatio - left.logEvidenceRatio
      || left.skillId.localeCompare(right.skillId));
    return {
      roleId: item.roleId,
      displayTitle: item.displayTitle,
      relativeScore: round(Math.exp(logScore - maximumLogScore) / normalizer, 8),
      trainingRecordCount: item.trainingRecordCount,
      evidence: {
        skillSignals,
        scoreSemantics: 'Relative softmax score over supported observed-title labels; uncalibrated and not a probability of employment.',
      },
    };
  });

  return {
    model: {
      id: modelArtifact.modelId,
      version: modelArtifact.modelVersion,
      family: modelArtifact.modelFamily,
      trainedModel: true,
      sourceArchiveRunId: modelArtifact.sourceArchiveRunId,
      trainedTitleClasses: modelArtifact.coverage.trainedTitleClasses,
      trainingRecords: modelArtifact.trainingRecordCount,
      priorWeight: modelArtifact.hyperparameters.priorWeight,
      trainingCoveragePercent: modelArtifact.coverage.trainingCoveragePercent,
      validation: {
        evaluatedRecords: validation.evaluatedRecords,
        top1Accuracy: validation.top1Accuracy,
        priorOnlyTop1Accuracy: validation.priorOnlyTop1Accuracy,
        top5Accuracy: validation.top5Accuracy,
        priorOnlyTop5Accuracy: validation.priorOnlyTop5Accuracy,
        selectionCriterion: modelArtifact.evaluation.selectionCriterion,
      },
      heldOutTest: modelArtifact.evaluation.heldOutTest,
    },
    recognizedSkills: modeledSkills.map(({ skillId, name }) => ({ skillId, name })),
    unmodeledSkills: unmodeledSkills.map(({ skillId, name }) => ({ skillId, name })),
    predictions,
    limitations: modelArtifact.limitations,
  };
}

module.exports = { getModelStatus, predictRoleTitles };
