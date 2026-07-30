# VLN and Embodied-Navigation Analysis

Read this reference for VLN, embodied navigation, Habitat, Matterport3D, ROS,
continuous-control, or simulator-based papers.

## Task setting

Identify:

- discrete graph, continuous environment, aerial, outdoor, or real-robot task;
- simulator and scene-dataset versions;
- instruction source and language coverage;
- observation modalities, camera height/FOV, sensors, and panoramic processing;
- discrete, waypoint, velocity, or low-level action space;
- stop action, collision handling, backtracking, and episode limits;
- seen/unseen, validation/test, and zero-shot/generalization conditions.

## Method map

Map paper concepts and code for:

- visual and language encoders;
- cross-modal fusion;
- history, recurrent state, episodic memory, or video context;
- topological, metric, BEV, semantic, or learned map;
- waypoint prediction and local control;
- global planning, graph search, backtracking, and stop policy;
- world-model prediction or future-state modeling;
- imitation learning, reinforcement learning, test-time adaptation, or
  reinforcement fine-tuning.

## Data and assets

Verify R2R, RxR, REVERIE, CVDN, VLN-CE, HM3D, Matterport3D, Gibson, HA3D, or
other datasets individually. Record licenses, access forms, splits, connectivity
graphs, rendered features, detector features, annotations, simulator builds,
scene assets, and checkpoint dependencies.

Do not treat R2R or VLN-CE as model names. Distinguish a benchmark/task setting
from the implementation evaluated on it.

## Evaluation

Extract definitions and code implementations for applicable metrics:

- Navigation Error (`NE`);
- Success Rate (`SR`);
- Oracle Success Rate (`OSR`);
- Success weighted by Path Length (`SPL`);
- `nDTW`, `SDTW`, and `CLS`;
- collision, distance-to-goal, progress, social-navigation, or task-specific
  metrics.

Check success radius, geodesic versus Euclidean distance, path discretization,
episode filtering, number of runs, seed handling, and leaderboard protocol.

## Reproduction risks

Flag:

- unavailable Matterport3D/HM3D licenses or scene data;
- simulator, Habitat, CUDA, compiler, or rendering-version coupling;
- precomputed visual features whose extractor/checkpoint is unspecified;
- mismatch between discrete training and continuous evaluation;
- missing waypoint, detector, depth, segmentation, or language checkpoints;
- GUI-only simulator paths versus EGL/OSMesa/Xvfb headless support;
- real-robot calibration, sensors, safety layers, or hardware not represented
  in simulation.
