What's the deal here?

This is an experimental branch to get Imagr working in Recovery boot and Internet Recovery boot. Since those environments don't include the Python framework, we need to bundle it with Imagr itself.

Once you've cloned this repo and checked out the embedded-python-framework branch, you'll need to provide a copy of a relocatable Python framework.

Use this project to make one:
https://github.com/gregneagle/relocatable-python

Copy the resulting framework into Imagr/Resources

Open the Imagr.xcodeproj in Xcode and build the project.

See the README in the "Imagr_for_Recovery" folder for more notes.

