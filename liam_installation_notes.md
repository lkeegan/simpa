# Installation notes on compgpu

## simpa within conda env

Environment has cuda, pytorch and all simpa deps available on conda-forge pre-installed:

```
gh repo clone simpa
cd simpa
micromamba create -f environment.yml
micromamba activate simpa
pip install .
```

## mcx

To build using nvcc and libs from simpa conda env, need to set `CUDA_HOME` make arg to `CONDA_PREFIX`:

```
gh repo clone IMSY-DKFZ/mcx
cd mcx/src
make CUDA_HOME=$CONDA_PREFIX -j
```

To run mcx using libs from conda env also need to set `LD_LIBRARY_PATH` at runtime:

```
LD_LIBRARY_PATH=$CONDA_PREFIX/lib ldd ../bin/mcx
```

## k-wave

Download and extract k-wave toolbox. Also download pre-compiled binaries,
chmod +x them, and put them in ~/k-Wave/binaries folder.

Then make a folder `~/matlab` and add a file startup.m that adds the k-wave folder to the matlab path:

```
addpath ('/export/home/lkeegan/k-Wave');
```

When running matlab, set startup dir to ~/matlab so startup.m is automatically loaded (unclear if this needs doing again for each session but path seems to persist between calls to matlab so far):

```
matlab -sd /export/home/lkeegan/matlab
```

### patch matlab hdf5 support

Apparently matlab 2020a hdf5 support is broken,
so download a patched version of `h5writeatt.m` from
http://www.k-wave.org/forum/topic/error-reading-h5-files-when-using-binaries#post-7645
and add it to the `~/matlab` folder

### re-compile k-wave cuda code

Pre-compiled binaries only have support up to sm_75, need sm_80 for A100, so need to compile the cuda sources (as well as hdf5):

#### hdf5

```
wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.8/hdf5-1.8.21/src/hdf5-1.8.21.tar.gz
tar xf hdf5-1.8.21.tar.gz
cd hdf5-1.8.21
./configure --enable-hl --prefix=/export/home/lkeegan/hdf5
make -j
make install
```

#### k-wave cuda

edit `kspaceFirstOrder-CUDA/Makefile`:

- replace spaces with tabs for last few items if make "missing separator" error occurs
- remove < sm_52, add sm_80, sm_86 to archs

Then copy system static libz.a and libsz.a libs (`whereis libz.a`) to /export/home/lkeegan/lib/.

Now can build, by default all libs statically linked apart from cuda ones:

```
make CUDA_DIR=$CONDA_PREFIX EBROOTHDF5=/export/home/lkeegan/hdf5 EBROOTZLIB=/export/home/lkeegan SZIP_DIR=/export/home/lkeegan
```

Note: will again need to modify LD_LIBRARY_PATH at runtime to pick up cuda libs from conda (but may also work with system libs):

```
LD_LIBRARY_PATH=$CONDA_PREFIX/lib ./kspaceFirstOrder-CUDA --version
```

## path config

create `path_config.env` containing:

```
SAVE_PATH=/export/home/lkeegan/simpa/save_path
MCX_BINARY_PATH=/export/home/lkeegan/mcx/bin/mcx
MATLAB_BINARY_PATH=/usr/local/bin/matlab
```

## run examples

e.g.

```
python simpa_examples/minimal_optical_simulation.py
```
