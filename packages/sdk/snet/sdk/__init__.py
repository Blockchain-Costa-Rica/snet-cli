import google.protobuf.internal.api_implementation

google.protobuf.internal.api_implementation.Type = lambda: 'python'

from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
_sym_db.RegisterMessage = lambda x: None


import json
import base64
from urllib.parse import urljoin

import web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from rfc3986 import urlparse
import ipfsapi
from web3.datastructures import AttributeDict

from snet.sdk.service_client import ServiceClient
from snet.sdk.account import Account
from snet.sdk.mpe_contract import MPEContract
from snet.sdk.payment_channel_management_strategies.default import PaymentChannelManagementStrategy

from snet.snet_cli.utils import get_contract_object
from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash
from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json


class SnetSDK:
    """Base Snet SDK"""
    def __init__(
        self,
        config
    ):
        self._config = config

        # Instantiate Ethereum client
        eth_rpc_endpoint = self._config.get("eth_rpc_endpoint", "https://mainnet.infura.io")
        provider = web3.HTTPProvider(eth_rpc_endpoint)
        self.web3 = web3.Web3(provider)
        self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)

        self.mpe_contract = MPEContract(self.web3)

        # Instantiate IPFS client
        ipfs_rpc_endpoint = self._config.get("ipfs_rpc_endpoint", "https://ipfs.singularitynet.io:80")
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        self.ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port)

        self.registry_contract = get_contract_object(self.web3, "Registry.json")
        self.account = Account(self.web3, config, self.mpe_contract)


    def create_service_client(self, org_id, service_id, service_stub, group_name=None, payment_channel_management_strategy=PaymentChannelManagementStrategy, options=None):
        if options is None:
            options = dict()

        org_metadata = self.get_org_metadata(org_id)
        service_metadata= self.get_service_metadata(org_id,service_id)
        group = self.get_group_from_org_metadata(org_metadata)
        strategy = payment_channel_management_strategy(self)
        service_client = ServiceClient(self, org_metadata,service_metadata, group, service_stub, strategy, options)
        return service_client


    def get_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri, tags) = self.registry_contract.functions.getServiceRegistrationById(bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()

        if found is not True:
            raise Exception('No service "{}" found in organization "{}"'.format(service_id, org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self.ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata
    def _get_organization_metadata_from_registry(self, org_id):
        rez = self._get_organization_registration(org_id)
        metadata_hash = bytesuri_to_hash(rez["orgMetadataURI"])
        metadata = get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        return json.loads(metadata)

    def _get_organization_registration(self, org_id):
        params = [type_converter("bytes32")(org_id)]
        rez = self.call_contract_command(
            "Registry", "getOrganizationById", params)
        if (rez[0] == False):
            raise Exception("Cannot find  Organization with id=%s" % (
                self.args.org_id))
        return {"orgMetadataURI": rez[2]}

    def get_org_metadata(self,org_id):
        return self.__get_organization_metadata_from_registry(org_id)

    def get_group_from_org_metadata(self,org_metadata,group_name):
        return org_metadata.groups
