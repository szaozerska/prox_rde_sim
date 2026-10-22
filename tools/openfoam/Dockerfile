# Resolve this official Foundation image to a digest before the recorded build.
ARG OPENFOAM_IMAGE=openfoam/openfoam8-graphical-apps:latest
FROM ${OPENFOAM_IMAGE}
USER root
SHELL ["/bin/bash", "-c"]
COPY foam-env.sh /opt/foam-env.sh
COPY detonationFoam /opt/src/detonationFoam
RUN source /opt/foam-env.sh && \
    mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" && \
    cd /opt/src/detonationFoam/applications/solvers/detonationFoam_V2.0 && \
    wmake -j 2 dynamicMesh2D/dynamicMesh && \
    wmake -j 2 dynamicMesh2D/dynamicFvMesh && \
    wmake -j 2 DLBFoam-1.0-1.0_OF8/src/thermophysicalModels/chemistryModel && \
    wmake -j 2 fluxSchemes_improved && \
    wmake -j 2 && \
    detonationFoam_V2.0 -help && \
    ! ldd "$FOAM_USER_APPBIN/detonationFoam_V2.0" | grep 'not found'
WORKDIR /case
ENTRYPOINT ["/bin/bash", "-c", "source /opt/foam-env.sh && exec \"$@\"", "bash"]
