# Robotics and VLN Readiness

Read this reference only for embodied AI, VLN, ROS, robotics, simulation, 3D
perception, or custom CUDA projects.

## Habitat and VLN

Check:

- Habitat-Lab and Habitat-Sim version pairing;
- Python, NumPy, Magnum, CUDA, and headless build compatibility;
- whether the project expects Conda binaries, source builds, or containers;
- R2R, RxR, VLN-CE, HM3D, MP3D, Gibson, and Matterport identifiers;
- dataset splits, scene versions, connectivity graphs, and benchmark metrics;
- Matterport3D/HM3D/Gibson license acceptance and download credentials;
- whether MatterSim must compile and which compiler/CUDA/Python ABI it uses;
- whether released checkpoints match tokenizer, visual encoder, action space,
  simulator version, and dataset preprocessing;
- panorama, video, sequence length, batch size, and map-resolution effects on
  RAM and VRAM;
- whether inference can run from prerecorded observations without a simulator.

Do not describe licensed scene data as freely redistributable. Report license
and credential requirements without exposing credential values.

## ROS

Check:

- ROS 1 versus ROS 2;
- ROS distribution versus supported Ubuntu release;
- system Python versus project environment assumptions;
- `package.xml`, rosdep keys, `.repos`, colcon mixins, overlays, and workspaces;
- DDS/RMW implementation and network assumptions;
- message, service, action, TF frame, clock, and bag-format compatibility;
- hardware drivers and udev/system-service requirements;
- whether real-robot nodes can be mocked or replaced with bags for offline tests.

Treat ROS/Ubuntu pairing as hard when binary packages or middleware require it.
Do not recommend changing the host OS before evaluating a container, WSL, or
separate server path.

## Gazebo

Distinguish:

- Gazebo Classic from modern Gazebo;
- `gazebo_ros_pkgs` from `ros_gz`;
- world, model, plugin, SDF, and transport versions;
- GUI client requirements from server/headless simulation;
- rendering backend and GPU forwarding requirements.

Do not assume Classic plugins work in modern Gazebo.

## Isaac Sim and Isaac Lab

Check:

- exact Isaac Sim/Isaac Lab pairing;
- driver, Vulkan, RTX, GPU, and VRAM requirements;
- Python supplied by Isaac Sim versus external Python;
- extension cache and asset-server requirements;
- native headless or livestream capability;
- container support and display/GPU forwarding.

Treat major Isaac version coupling as hard unless an official compatibility
matrix says otherwise.

## AirSim and Unreal

Check:

- AirSim fork and commit;
- Unreal Engine version and project/plugin coupling;
- OS and compiler support;
- packaged simulator availability;
- GPU/display requirements;
- headless or offscreen rendering path;
- whether prerecorded sensor data can replace live simulation.

## Sensors and real robots

Record assumptions about:

- RGB, depth, stereo, LiDAR, IMU, odometry, GPS, and camera intrinsics;
- TF frame names, coordinate conventions, rates, timestamps, and synchronization;
- calibration files and device SDKs;
- robot model, control interface, safety layer, and network transport;
- whether deployment-only nodes are separable from model inference.

Classify unavailable hardware as a blocker only for workflows that truly require
it.

## CUDA and native extensions

Inspect build and runtime coupling for:

- detectron2;
- mmcv and mmcv-full;
- xformers and flash-attn;
- MinkowskiEngine and sparse convolutions;
- point-cloud, voxel, deformable-attention, and custom PyTorch extensions;
- CUDA architecture flags and prebuilt wheel indexes;
- GCC/MSVC, CMake, Ninja, and C++ ABI assumptions.

Confirm support for the installed GPU compute capability. Distinguish wheel
availability from source-build feasibility. Ask before compiling.

## Distributed and resource assumptions

Check:

- `torchrun`, Slurm, MPI, NCCL, and multi-node configuration;
- effective batch size, gradient accumulation, precision, and optimizer state;
- dataset staging and checkpoint size;
- expected GPU count, VRAM, RAM, disk, and runtime;
- whether evaluation uses a single GPU while training assumes multiple GPUs.

If the repository provides no measurements, label resource profiles as
estimates and explain the comparison or scaling rule used.

## Rendering classification

Use:

- `NATIVE_HEADLESS` when no display or rendering context is required;
- `EGL_OR_OSMESA` for supported offscreen rendering;
- `XVFB` when an X server shim is required;
- `GUI_REQUIRED` for interactive visualization or teleoperation;
- `UNKNOWN` when the renderer or plugin path is not established.

Test rendering only with a minimal scene or existing asset and only when the
command is known to be cheap.
