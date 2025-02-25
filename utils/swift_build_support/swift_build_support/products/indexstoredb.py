# swift_build_support/products/indexstoredb.py -------------------*- python -*-
#
# This source file is part of the Swift.org open source project
#
# Copyright (c) 2014 - 2017 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors
#
# ----------------------------------------------------------------------------

import os

from build_swift.build_swift.constants import MULTIROOT_DATA_FILE_PATH

from . import cmark
from . import foundation
from . import libcxx
from . import libdispatch
from . import llbuild
from . import llvm
from . import product
from . import swift
from . import swiftpm
from . import swiftsyntax
from . import xctest
from .. import shell
from .. import targets


class IndexStoreDB(product.Product):
    @classmethod
    def product_source_name(cls):
        return "indexstore-db"

    @classmethod
    def is_build_script_impl_product(cls):
        return False

    @classmethod
    def is_before_build_script_impl_product(cls):
        return False

    @classmethod
    def is_swiftpm_unified_build_product(cls):
        return True

    def should_build(self, host_target):
        return True

    def build(self, host_target):
        run_build_script_helper('build', host_target, self, self.args)

    def should_test(self, host_target):
        return self.args.test_indexstoredb

    def test(self, host_target):
        run_build_script_helper('test', host_target, self, self.args,
                                self.args.test_indexstoredb_sanitize_all)

    def should_install(self, host_target):
        return False

    def install(self, host_target):
        pass

    def has_cross_compile_hosts(self):
        return False

    @classmethod
    def get_dependencies(cls):
        return [cmark.CMark,
                llvm.LLVM,
                libcxx.LibCXX,
                swift.Swift,
                libdispatch.LibDispatch,
                foundation.Foundation,
                xctest.XCTest,
                llbuild.LLBuild,
                swiftpm.SwiftPM,
                swiftsyntax.SwiftSyntax]


def run_build_script_helper(action, host_target, product, args,
                            sanitize_all=False, clean=True):
    script_path = os.path.join(
        product.source_dir, 'Utilities', 'build-script-helper.py')

    install_destdir = product.host_install_destdir(host_target)
    toolchain_path = product.native_toolchain_path(host_target)
    is_release = product.is_release()
    configuration = 'release' if is_release else 'debug'
    helper_cmd = [
        script_path,
        action,
        '--package-path', product.source_dir,
        '--build-path', product.build_dir,
        '--configuration', configuration,
        '--toolchain', toolchain_path,
        '--ninja-bin', product.toolchain.ninja,
        '--multiroot-data-file', MULTIROOT_DATA_FILE_PATH,
    ]
    if args.verbose_build:
        helper_cmd.append('--verbose')

    if sanitize_all:
        helper_cmd.append('--sanitize-all')
    elif args.enable_asan:
        helper_cmd.extend(['--sanitize', 'address'])
    elif args.enable_ubsan:
        helper_cmd.extend(['--sanitize', 'undefined'])
    elif args.enable_tsan:
        helper_cmd.extend(['--sanitize', 'thread'])

    if not clean:
        helper_cmd.append('--no-clean')

    # Pass Cross compile host info unless we're testing.
    # It doesn't make sense to run tests of the cross compile host.
    if product.has_cross_compile_hosts() and action != 'test':
        if product.is_darwin_host(host_target):
            if len(args.cross_compile_hosts) != 1:
                raise RuntimeError("Cross-Compiling indexstoredb to multiple " +
                                   "targets is not supported")
            helper_cmd += ['--cross-compile-host', args.cross_compile_hosts[0]]
        elif product.is_cross_compile_target(host_target):
            helper_cmd.extend(['--cross-compile-host', host_target])
            build_toolchain_path = install_destdir + args.install_prefix
            resource_dir = '%s/lib/swift' % build_toolchain_path
            helper_cmd += [
                '--cross-compile-config',
                targets.StdlibDeploymentTarget.get_target_for_name(host_target).platform
                .swiftpm_config(args, output_dir=build_toolchain_path,
                                swift_toolchain=toolchain_path,
                                resource_path=resource_dir)
            ]

    if action == 'install' and product.product_name() == "sourcekitlsp":
        helper_cmd.extend([
            '--prefix', install_destdir + args.install_prefix
        ])

    shell.call(helper_cmd)
