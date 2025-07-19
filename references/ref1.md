# Introduction

Hi everyone! Today I'm going to be giving you a crash course in video processing using Python. Coming out of this talk, you'll be able to take video from pretty much any source, decode it, apply visual effects, and display it on-screen. To do this, we're going to be using a library named GStreamer, an incredibly powerful and versatile framework. This is the same tool that the pros use, but don't feel intimidated! GStreamer actually makes it very easy to do impressive things with video and you'll be well on your way to making something great in just the time it takes to watch this talk.

If you fall behind at any point during the live presentation, don't worry! I have a text version of this talk available with the same content and more. There should be a link in the description.

# Installing Dependencies

Let's start by installing everything we'll need to start using GStreamer in Python. This is probably the hardest part, so if you managed to do it before this talk, it's all smooth sailing from here! If not, no worries! I'm going to go through how to install everything on Windows 10 right here. I would recommend opening up the text version of this talk, because I have links to the stuff we'll be downloading and you'll probably want to copy and paste a few of the long commands we'll be running. If you're using macOS or Linux, you'll find separate instructions for how to install everything for those platforms there as well.

## Windows 10

We're going to be using a tool called MSYS2 to download everything we need to get started. MSYS2 makes it easy to set up development environments on Windows.

Download the latest stable release of MSYS2 from [the releases page][msys2 releases]. At the time of writing, the latest release (2020-09-03) is available [here][msys2 download]. Then run the installer, accepting all the defaults, but unchecking "Run MSYS2".

Once it's installed, start "MSYS2 MinGW 64-bit" from the Start Menu. This will open up the MSYS2 terminal.

Let's get MSYS2 up-to-date by running the following command:

```bash
pacman -Syu
```

After this command finishes, it may need to close. Just open it right back up again!

Now, we're ready to install everything we need! The following command installs GStreamer, some plugins, Python, and the PyGObject library.

```bash
pacman -S mingw-w64-x86_64-gstreamer mingw-w64-x86_64-gst-devtools mingw-w64-x86_64-gst-plugins-{base,good,bad,ugly} mingw-w64-x86_64-python3 mingw-w64-x86_64-python3-gobject
```

Finally, you're going to need a text editor to write code! I use [Visual Studio Code][vscode] but you can use whatever you like. Even Notepad is fine!

[msys2 releases]: https://github.com/msys2/msys2-installer/releases
[msys2 download]: https://github.com/msys2/msys2-installer/releases/download/2020-09-03/msys2-x86_64-20200903.exe
[vscode]: https://code.visualstudio.com/

## macOS

Homebrew, a package manager for macOS, makes it easy to install everything we need for this project. To install Homebrew, simply run the following command in the terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
```

Then, run this command to install everything we need:

```bash
brew install gstreamer gst-devtools gst-plugins-{base,good,bad,ugly} python@3 pygobject3
```

## Ubuntu, Debian, elementary OS, Pop!_OS

Installing everything we need on Ubuntu and related operating systems is easy! Just run the following command in the terminal:

```bash
sudo apt install libgstreamer1.0-0 gstreamer1.0-plugins-{base,good,bad,ugly} gstreamer1.0-tools python3-gi gir1.2-gstreamer-1.0
```

## Arch Linux, Manjaro

Like Ubuntu, installing everything on Arch Linux or Manjaro is just a matter of running the following command in the terminal:

```bash
sudo pacman -S gstreamer gst-plugins-{base,good,bad,ugly} python python-gobject
```

# Digital Video Concepts

While you're waiting on everything to install, let's take a step back. A wise scholar once said: Before you decode the video, you must understand the video. You must be the video.

At a fundamental level, video is presented to viewers as a list of images that are shown one after the other at a high enough speed for our eyes to see it as a moving picture. Pretty simple, right? Well, there's just one problem. Storing all these thousands and thousands of images takes up a huge amount of space. An average 10 minute YouTube video would require over 100 GB of storage, and a feature-length movie could take upwards of a terabyte! Where is our escape from this madness??

Well, luckily, mathematicians and computer scientists have found many clever and sophisticated ways to compress video data down to a fraction of its original size. These researchers have turned their work into standards that define exactly how their technology works and how video data that is compressed this way can be decoded. We call these standards "video compression formats", and some popular ones include H.264, VP8, and AV1 among many others.

All the while, other smart people needed to figure out in what way the compressed video data should be saved to a video file, or split into chunks and streamed over the internet. This resulted in the development of special formats that hold both the compressed video data and additional information, like the title of the video, its resolution, and other stuff. We call these "container formats", and some popular ones include MPEG-4 and WebM.

So, in the end, you use a video camera to record something, those raw images get compressed in a video compression format, and once you're done your video is wrapped up with a nice little bow using a container format. Now, the video file is ready to be stored on your computer or streamed out for all the world to see.

# GStreamer Concepts

Now that we know how video works, we can begin to understand how GStreamer lets us work with it. Working with GStreamer is kind of like creating an assembly line in a factory. Each step in the assembly line is in charge of doing one thing, and the results of one step are passed on to the next step until the process is complete. GStreamer calls this assembly line a "pipeline", and the steps are known as "elements".

Every pipeline starts with a source element, has some number of elements that process the data in the middle, and ends with a sink element. The source element is in charge of getting video data from somewhere, like a file on your computer or a video stream hosted online. That data is then passed to the next element, which does some processing on the data, and the result is passed on to the next element in the pipeline and so on. Finally, the fully processed data is passed to the sink element, which will take care of making the data available somewhere. That might involve saving it to your computer, hosting it as a live video stream, or passing it back to your application.

GStreamer has a lot of elements that do all kinds of different things. Each one has a name that we refer to it by, and certain rules governing what kinds of data it can take as input and what it produces as output.

Now, putting together one of these pipelines might sound hard, but GStreamer makes it pretty easy. All you have to do is give GStreamer a string with the names of each element you want in your pipeline, separated my exclamation marks. And that's it! GStreamer will take care of creating these elements and attaching them to each other.

# Let's Get to the Code

With all that background in mind, let's jump into the code. Now, we're going to be writing in Python but the GStreamer library is written in C so we're going to be using what's called a "binding". A binding is simply a library that allows you to use a library in one language from another language. GStreamer's Python binding library is called PyGObject, and we import it like this:

```python
import gi
```

Now we need to tell PyGObject the minimum version of GStreamer that our program requires, which the library shortens to "Gst". Once we've done that, we're ready to import the "Gst" module, as well as the "GLib" module which we will use shortly. Make sure to call `Gst.init()` to initialize GStreamer before doing anything else.

```python
gi.require_version("Gst", "1.0")

from gi.repository import Gst, GLib


Gst.init()
```

After that, we need to start the main loop. The main loop is in charge of handling events and doing some other background tasks. Here we'll start it in a new thread, so that we can do other things in our main thread.

```python
from threading import Thread

main_loop = GLib.MainLoop()
thread = Thread(target=main_loop.run)
thread.start()
```

Finally, we're ready to construct a simple pipeline! Like I mentioned earlier, all pipelines start with a source. Which source element we use will depend on where we want to get our video from. For now, let's try getting video from our webcam. On Windows, we can use the `ksvideosrc` element to do his. If you're on macOS, try `autovideosrc`. For Linux, it's `v4l2src`.

Then, we're going to follow that up with a `decodebin` element. This is a super helpful element that takes care of figuring out what container format and video compression format a source is providing, and handles decoding it for us into raw images.

Next let's add a `videoconvert` element, another handy tool that takes care of any format differences between the images that `decodebin` provides and what our next element expects.

Our pipeline is almost done! Just like how every pipeline starts with a source, they also end with a sink! Our sink of choice today will be `autovideosink`, which will display our webcam footage on-screen. 

```python
pipeline = Gst.parse_launch("ksvideosrc ! decodebin ! videoconvert ! autovideosink")
```

We've defined our pipeline, but we're not quite done yet! We still need to start the pipeline up. To do this, we use the `set_state` method, which asks the main loop that we started earlier to take care of initializing and playing our pipeline. All that work will be done in the background, so we can continue doing whatever we want in our program.

```python
pipeline.set_state(Gst.State.PLAYING)
```

For this example, all we're going to do is wait around while our webcam footage is being played on-screen until you stop the program. At that point, we'll ask the pipeline to stop and clean up by setting it to the `NULL` state. Then, finally, we'll stop the main loop we started earlier.

```python
try:
    while True:
        sleep(0.1)
except KeyboardInterrupt:
    pass

pipeline.set_state(Gst.State.NULL)
main_loop.quit()
```

Here's the example in full. Again, make sure to replace `ksvideosrc` with your platform's equivalent if you're not running on Windows.

```python
from threading import Thread

import gi

gi.require_version("Gst", "1.0")

from gi.repository import Gst, GLib


Gst.init()

main_loop = GLib.MainLoop()
thread = Thread(target=main_loop.run)
thread.start()

pipeline = Gst.parse_launch("ksvideosrc ! decodebin ! videoconvert ! autovideosink")
pipeline.set_state(Gst.State.PLAYING)

try:
    while True:
        sleep(0.1)
except KeyboardInterrupt:
    pass

pipeline.set_state(Gst.State.NULL)
main_loop.quit()
```

# Having Fun

Now that we've got our example application running, we can add some cool filters to our webcam stream! Some personal favorites of mine are `edgetv` and `rippletv`. Just make sure to add a `videoconvert` before and after them to ensure that the element is getting images in a format it's compatible with.

```python
pipeline = Gst.parse_launch("ksvideosrc ! decodebin ! videoconvert ! edgetv ! "
                            "videoconvert ! autovideosink")
```

# Doing Your Own Thing with Video

GStreamer has a huge number of fun and useful elements for just about everything, but what if you wanted to do something custom? Maybe you want to implement your own special filter, or send the images off to another service or library. For these cases, GStreamer provides the `appsink` element, which allows you to take data out of the pipeline. Let's check it out.

We're going to use our original webcam pipeline, but replace the `autovideosink` with `appsink`. We're going to give the element a name so that we can pull this element out of the pipeline and interact with it.

```python
pipeline = Gst.parse_launch("ksvideosrc ! decodebin ! videoconvert ! "
                            "appsink name=sink")
appsink = pipeline.get_by_name("sink")
```

Now, we can pull images out of the `appsink` using the `try_pull_sample` method.

```python
try:
    while True:
        sample = appsink.try_pull_sample(Gst.SECOND)
        if sample is None:
            continue
    
        print("Got a sample!")
except KeyboardInterrupt:
    pass
```

That's all I'm going to show you about `appsink` in this talk, just to whet your appetite. But, I have some more examples in the text version of this talk if this sounds like something your hack needs.

# Conclusion

And.. that's a wrap! Thanks so much for listening, and I hope you found it enjoyable. If you have any questions, please feel free to reach out to me on the sunhacks Discord. Again, my name is Tyler and I should be marked as a "mentor". Happy hacking!

# Extra Credit

## My pipeline isn't working. How do I find out why?

When GStreamer encounters a problem, it prints an error message to the console. However, by default, these logs are hidden. To see them, we need to set the `GST_DEBUG` environment variable.

For example, if you're running your program like this:

```bash
python3 main.py
```

Run it like this, instead:

```bash
GST_DEBUG=2 python3 main.py
```

However, reading GStreamer logs can sometimes feel like an art form. Feel free to reach out to me if you're having trouble understanding what these logs are telling you!
