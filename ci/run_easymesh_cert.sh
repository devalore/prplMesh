#!/bin/bash
# Simple wrapper script to easymesh_cert/run_test_file.sh
# which also updates to the latest prplmesh IPK, run the tests and
# uploads the results
###############################################################
# SPDX-License-Identifier: BSD-2-Clause-Patent
# Copyright (c) 2020 Tomer Eliyahu (Intel)
# This code is subject to the terms of the BSD+Patent license.
# See LICENSE file for more details.
###############################################################

scriptdir="$(cd "${0%/*}" && pwd)"
rootdir=$(realpath "$scriptdir/../")

# shellcheck source=functions.sh
. "$rootdir/tools/functions.sh"

usage() {
    echo "usage: $(basename $0) [-hboev] <test> [test]"
    echo "  options:"
    echo "      -h|--help - display this help."
    echo "      -b|--branch - prplmesh branch to use (default master latest)"
    echo "      -o|--log-folder - path to put the logs to (make sure it does not contain previous logs)."
    echo "      -e|--easymesh-cert - path to easymesh_cert repository (default ../easymesh_cert)"
    echo "      --owncloud-upload - whether or not to upload results to owncloud. (default: false)"
    echo "      --owncloud-path - relative path in the owncloud server to upload results to. (default: $OWNCLOUD_PATH)"
    echo "      -v|--verbose - set verbosity (ucc logs also redirected to stdout)"
    echo "      -s|--ssh - target device ssh name (defined in ~/.ssh/config). (default: $TARGET_DEVICE_SSH)"
    echo "'test' can either be a test name, or the path to a file containing"
    echo " test names (newline-separated)."
    echo
    echo "Multiple test files/names are allowed, and they can also be mixed."
    echo "For example, the following call would run the test 'MAP-5.3.1', and all the tests"
    echo "contained in the 'tests/all_controller_test.txt' file:"
    echo "$(basename "$0") MAP-5.3.1 tests/all_controller_test.txt"
    echo ""
    echo "The default is to run all agent certification tests."
    echo ""
    echo "Credentials for uploading to owncloud are taken from $HOME/.netrc"
    echo "Make sure it has a line like this:"
    echo "  machine ftp.essensium.com login <user> password <password>"
    echo ""
}

main() {
    OPTS=$(getopt -o 'hb:o:e:s:v' --long help,branch:,log-folder:,easymesh-cert:,owncloud-upload,owncloud-path:,ssh:,verbose -n 'parse-options' -- "$@")

    if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; usage; exit 1 ; fi

    eval set -- "$OPTS"

    while true; do
        case "$1" in
            -h | --help)            usage; exit 0;;
            -b | --branch)          BRANCH="$2"; shift 2;;
            -o | --log-folder)      LOG_FOLDER="$2"; shift 2;;
            -v | --verbose)         VERBOSE=true; VERBOSE_OPT="-v"; shift;;
            -e | --easymesh-cert)   EASYMESH_CERT_PATH="$2"; shift 2;;
            --owncloud-upload)      OWNCLOUD_UPLOAD=true; shift;;
            --owncloud-path)        OWNCLOUD_PATH="$2"; shift 2;;
            -s | --ssh)             TARGET_DEVICE_SSH="$2"; shift 2;;
            -- ) shift; break ;;
            * ) err "unsupported argument $1"; usage; exit 1;;
        esac
    done

    TESTS="$*"

    [ -n "$TESTS" ] || TESTS="$EASYMESH_CERT_PATH/tests/all_agent_tests.txt"
    [ -n "$LOG_FOLDER" ] || LOG_FOLDER="$EASYMESH_CERT_PATH/logs/$(date +%F_%H-%M-%S)"
    info "Logs location: $LOG_FOLDER"
    info "Tests to run: $TESTS"

    info "download latest ipk from branch $BRANCH"
    "$TOOLS_PATH"/download_ipk.sh --branch "$BRANCH" ${VERBOSE:+ -v} || {
        err "Failed to download prplmesh.ipk, abort"
        exit 1
    }
    
    info "prplmesh build info:"
    cat "$PRPLMESH_BUILDINFO"

    info "deploy latest ipk to $TARGET_DEVICE_SSH"
    "$TOOLS_PATH"/deploy_ipk.sh "$TARGET_DEVICE_SSH" "$PRPLMESH_IPK" || {
        err "Failed to deploy prplmesh.ipk, abort"
        exit 1
    }

    info "Start running tests"
    "$EASYMESH_CERT_PATH"/run_test_file.sh -o "$LOG_FOLDER" -d "$TARGET_DEVICE" "$TESTS" ${VERBOSE:+ -v}
    mv "$PRPLMESH_IPK" "$LOG_FOLDER"
    mv "$PRPLMESH_BUILDINFO" "$LOG_FOLDER"

    if [ -n "$OWNCLOUD_UPLOAD" ]; then
        info "Uploading $LOG_FOLDER to $OWNCLOUD_PATH"
        "$scriptdir"/upload_to_owncloud.sh "$OWNCLOUD_PATH" "$LOG_FOLDER" || {
            err "Failed to upload $LOG_FOLDER"
            exit 1
        }
    fi
    info "done"
}

BRANCH=master
PRPLMESH_IPK=prplmesh.ipk
PRPLMESH_BUILDINFO=prplmesh_buildinfo.txt
TOOLS_PATH="$rootdir/tools"
EASYMESH_CERT_PATH=$(realpath "$rootdir/../easymesh_cert")
TARGET_DEVICE="netgear-rax40"
TARGET_DEVICE_SSH="$TARGET_DEVICE-1"
OWNCLOUD_PATH=Nightly/agent_certification

main "$@"
