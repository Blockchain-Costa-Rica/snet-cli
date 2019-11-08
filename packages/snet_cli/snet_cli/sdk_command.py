import os
from pathlib import Path
from pathlib import PurePath
from tempfile import TemporaryDirectory

from snet.snet_cli.utils import bytes32_to_str
from snet.snet_cli.utils import compile_proto
from snet.snet_cli.utils import type_converter
from snet.snet_cli.utils_ipfs import bytesuri_to_hash
from snet.snet_cli.utils_ipfs import get_from_ipfs_and_checkhash
from snet.snet_cli.utils_ipfs import safe_extract_proto_from_ipfs
from snet_cli.mpe_service_command import MPEServiceCommand


class SDKCommand(MPEServiceCommand):
    def generate_client_library(self):

        if os.path.isabs(self.args.protodir):
            client_libraries_base_dir_path = PurePath(self.args.protodir)
        else:
            cur_dir_path = PurePath(os.getcwd())
            client_libraries_base_dir_path = cur_dir_path.joinpath(self.args.protodir)

        os.makedirs(client_libraries_base_dir_path, exist_ok=True)

        # Create service client libraries path
        library_language = self.args.language
        library_org_id = self.args.org_id
        library_service_id = self.args.service_id

        library_dir_path = client_libraries_base_dir_path.joinpath(
            library_org_id, library_service_id, library_language
        )

        metadata = self._get_service_metadata_from_registry()
        model_ipfs_hash = metadata["model_ipfs_hash"]

        with TemporaryDirectory() as temp_dir:
            temp_dir_path = PurePath(temp_dir)
            proto_temp_dir_path = temp_dir_path.joinpath(
                library_org_id, library_service_id, library_language
            )
            safe_extract_proto_from_ipfs(
                self._get_ipfs_client(), model_ipfs_hash, proto_temp_dir_path
            )

            # Compile proto files
            compile_proto(
                Path(proto_temp_dir_path),
                library_dir_path,
                target_language=self.args.language,
            )

        self._printout(
            'client libraries for service with id "{}" in org with id "{}" generated at {}'.format(
                library_service_id, library_org_id, library_dir_path
            )
        )
