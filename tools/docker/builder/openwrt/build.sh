#!/bin/sh -e

scriptdir="$(cd "${0%/*}"; pwd)"
rootdir="${scriptdir%/*/*/*/*}"

. "${rootdir}/tools/functions.sh"

usage() {
    echo "usage: $(basename $0) -d <target_device> [-hfiortv]"
    echo "  options:"
    echo "      -h|--help - show this help menu"
    echo "      -b|--build-options - add docker build options"
    echo "      -d|--target-device the device to build for"
    echo "      -i|--image - build the docker image only"
    echo "      -o|--openwrt-version - the openwrt version to use"
    echo "      -r|--openwrt-repository - the openwrt repository to use"
    echo "      -t|--tag - the tag to use for the builder image"
    echo "      -v|--verbose - verbosity on"
    echo " -d is always required."
    echo ""
    echo "The following environment variables will affect the build:"
    echo " - PRPL_FEED: the prpl feed that will be used to install prplMesh."
    echo "   default: $PRPL_FEED"
    echo " - INTEL_FEED: only used for targets which needs the additional intel feed."
    echo "   default: empty"
}

build_image() {
    # We first need to build the corresponding images
    docker build --tag "$image_tag" \
           --build-arg OPENWRT_REPOSITORY \
           --build-arg OPENWRT_VERSION \
           --build-arg TARGET_SYSTEM \
           --build-arg SUBTARGET \
           --build-arg TARGET_PROFILE \
           --build-arg PRPL_FEED \
           --build-arg PRPLMESH_VARIANT \
           --build-arg INTEL_FEED \
           --build-arg BASE_CONFIG \
           $BUILD_OPTIONS \
           "$scriptdir/"
}

build_prplmesh() {
    build_dir="$1"
    container_name="prplmesh-builder-${TARGET_DEVICE}-$(uuidgen)"
    dbg "Container name will be $container_name"
    trap 'docker rm -f $container_name' EXIT
    docker run -i \
           --name "$container_name" \
           -e TARGET_SYSTEM \
           -e SUBTARGET \
           -e TARGET_PROFILE \
           -e OPENWRT_VERSION \
           -e PRPLMESH_VERSION \
           -v "$scriptdir/scripts:/home/openwrt/openwrt/build_scripts/:ro" \
           -v "${rootdir}:/home/openwrt/prplMesh_source:ro" \
           "$image_tag" \
           ./build_scripts/build.sh
    mkdir -p "$build_dir"
    # Note: docker cp does not support globbing, so we need to copy the folder
    docker cp "${container_name}:/home/openwrt/openwrt/artifacts/" "$build_dir"
    mv "$build_dir/artifacts/"* "$build_dir"
    rm -r "$build_dir/artifacts/"
}

main() {

    if ! command -v uuidgen > /dev/null ; then
        err "You need uuidgen to use this script. Please install it and try again."
        exit 1
    fi

    OPTS=`getopt -o 'hb:d:io:r:t:v' --long help,build-options:,device:,image,openwrt-version:,openwrt-repository:,tag:,verbose -n 'parse-options' -- "$@"`

    if [ $? != 0 ] ; then err "Failed parsing options." >&2 ; usage; exit 1 ; fi

    eval set -- "$OPTS"

    SUPPORTED_TARGETS="turris-omnia glinet-b1300 netgear-rax40"

    while true; do
        case "$1" in
            -h | --help)               usage; exit 0; shift ;;
            -b | --build-options)      BUILD_OPTIONS="$2"; shift; shift ;;
            -d | --target-device)      TARGET_DEVICE="$2"; shift ; shift ;;
            -i | --image)              IMAGE_ONLY=true; shift ;;
            -o | --openwrt-version)    OPENWRT_VERSION="$2"; shift; shift ;;
            -r | --openwrt-repository) OPENWRT_REPOSITORY="$2"; shift; shift ;;
            -t | --tag)                TAG="$2"; shift ; shift ;;
            -v | --verbose)            VERBOSE=true; shift ;;
            -- ) shift; break ;;
            * ) err "unsupported argument $1"; usage; exit 1 ;;
        esac
    done

    case "$TARGET_DEVICE" in
        turris-omnia)
            TARGET_SYSTEM=mvebu
            SUBTARGET=cortexa9
            TARGET_PROFILE=DEVICE_cznic_turris-omnia
            ;;
        glinet-b1300)
            TARGET_SYSTEM=ipq40xx
            SUBTARGET=generic
            TARGET_PROFILE=DEVICE_glinet_gl-b1300
            ;;
        netgear-rax40)
            TARGET_SYSTEM=intel_mips
            SUBTARGET=xrx500
            TARGET_PROFILE=DEVICE_NETGEAR_RAX40
            PRPLMESH_VARIANT="-dwpal"
            PRPL_FEED="https://git.prpl.dev/prplmesh/iwlwav.git^acc744ea7c3f678a9f5f7f6b6904c167afceb5b7"
            INTEL_FEED="https://git.prpl.dev/prplmesh/feed-intel.git^e3eca4e93286eb4346f0196b2816a3be97287482"
            BASE_CONFIG=gcc8
            ;;
        *)
            err "Unknown target device: $TARGET_DEVICE"
            info "Currently supported targets are:"
            for i in $SUPPORTED_TARGETS ; do
                info "$i"
            done
            exit 1
            ;;
    esac

    dbg "BUILD_OPTIONS=$BUILD_OPTIONS"
    dbg "OPENWRT_REPOSITORY=$OPENWRT_REPOSITORY"
    dbg "OPENWRT_VERSION=$OPENWRT_VERSION"
    dbg "BASE_CONFIG=$BASE_CONFIG"
    dbg "PRPL_FEED=$PRPL_FEED"
    dbg "INTEL_FEED=$INTEL_FEED"
    dbg "IMAGE_ONLY=$IMAGE_ONLY"
    dbg "TARGET_DEVICE=$TARGET_DEVICE"
    dbg "TAG=$TAG"
    dbg "TARGET_SYSTEM=$TARGET_SYSTEM"
    dbg "SUBTARGET=$SUBTARGET"
    dbg "TARGET_PROFILE=$TARGET_PROFILE"
    dbg "PRPLMESH_VARIANT=$PRPLMESH_VARIANT"

    if [ -n "$TAG" ] ; then
        image_tag="$TAG"
    else
        image_tag="prplmesh-builder-${TARGET}:${OPENWRT_VERSION}"
        dbg "image tag not set, using default value $image_tag"
    fi

    export OPENWRT_REPOSITORY
    export OPENWRT_VERSION
    export TARGET_SYSTEM
    export SUBTARGET
    export TARGET_PROFILE
    # We want to exclude tags from the git-describe output because we
    # have no relevant tags to use at the moment.
    # The '--exclude' option of git-describe is not available on older
    # git version, so we use sed instead.
    PRPLMESH_VERSION="$(git describe --always --dirty | sed -e 's/.*-g//')"
    export PRPLMESH_VERSION
    export PRPL_FEED
    export PRPLMESH_VARIANT
    export INTEL_FEED
    export BASE_CONFIG

    if [ $IMAGE_ONLY = true ] ; then
        build_image
        exit $?
    fi

    build_image
    build_prplmesh "$rootdir/build/$TARGET_DEVICE"

}

IMAGE_ONLY=false
VERBOSE=false
BUILD_OPTIONS=""
OPENWRT_REPOSITORY='https://git.prpl.dev/prplmesh/prplwrt.git'
OPENWRT_VERSION='9d2efd'
PRPL_FEED='https://git.prpl.dev/prplmesh/iwlwav.git^6749d406d243465e06b4f518767b2d1b9372e3f5'
INTEL_FEED=""
BASE_CONFIG=default

main "$@"
