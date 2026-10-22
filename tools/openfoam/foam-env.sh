# Source this inside the pinned Linux image (bash, not the macOS shell).
source /opt/openfoam8/etc/bashrc
export FOAM_USER_APPBIN=/opt/detonationfoam/bin
export FOAM_USER_LIBBIN=/opt/detonationfoam/lib
export PATH="$FOAM_USER_APPBIN:$PATH"
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
