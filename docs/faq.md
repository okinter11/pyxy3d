# FAQ

### Does it do real-time processing?

While the data processing pipeline is designed with the ultimate goal of real-time tracking, the current version does not support it. The processing demands of landmark detection across concurrent frames currently throttles the frame rate to such an extent that I don't consider this a worthile investment of time at the moment. As a stack of hardware/tracking algorithm emerges that shows a viable path to a scaleable system, this will get bumped as a priority. If you have expertise in this area and are interested in contributing, please consider opening up a thread in the [discussions](https://github.com/mprib/pyxy3d/discussions) to start a conversation.

### Can I process videos I pre-recorded with GoPros, etc?

Not currently, but this feature is planned for near-term roll out. Processing videos offline will enable the use of more cameras and higher frame rates and resolutions, but it also requires some method of frame synchronization and presents the need to perform calibration from pre-recorded videos. This is a development priority, but not currently implemented. I aim to create an API that will support such post-processing in the future so that Pyxy3D could be used programmatically by third-party Python processing pipelines.

### Can I use my smartphone as a camera?

Unfortunately, no. Supporting such input streams would present a unique challenge that would detract from the development of core processing. Including this ability is not a priority for development.

### Which webcam should I purchase?

I would recommend starting small and cheap and go from there. Start with whatever webcams you currently have access to. Conduct tests with two cameras to get a feel of how things run on your local system before throwing down for more. Scale out from there.

I will note that I have had success with the EMeet HD1080p cameras, which are reasonably priced (~$25 on Amazon). More expensive cameras with additional features such as autofocus have presented complications in my experience. If you have had a positive or negative experience with a specific webcam, kindly share it on our [discussions](https://github.com/mprib/pyxy3d/discussions) page.

### Can the software export to Blender (or Unreal/Maya/etc)?

Currently, the software only exports unfiltered 3D estimates in `csv` and `trc` formats. The `trc` format is designed for biomechanists. Those interested in creating an output pipeline to other formats may find the 'csv' files a good starting point and I invite you to open up a [discussion](https://github.com/mprib/pyxy3d/discussions) if you would like to talk through code.

### What is happening with my data? Are you storing videos I record?

Absolutely not. All operations are performed locally on your machine. An imagined future use-case for this package is as a tool that could be used in clinical settings or human subjects research. Data privacy is absolutely critical under those circumstances. The commitment that **you will always control your data** is at the heart of this project. 

