"""
Cloud Provider Integration for ag3ntwerk.

Provides unified interface for AWS, GCP, and Azure.

Requirements:
    - AWS: pip install boto3
    - GCP: pip install google-cloud-storage google-cloud-compute
    - Azure: pip install azure-identity azure-mgmt-compute azure-storage-blob

Cloud is ideal for:
    - Infrastructure management
    - Resource monitoring
    - Cost tracking
    - Multi-cloud operations
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Cloud providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


@dataclass
class AWSConfig:
    """AWS configuration."""

    access_key_id: str = ""
    secret_access_key: str = ""
    region: str = "us-east-1"
    profile: str = ""  # Use profile instead of keys


@dataclass
class GCPConfig:
    """GCP configuration."""

    project_id: str = ""
    credentials_file: str = ""
    region: str = "us-central1"


@dataclass
class AzureConfig:
    """Azure configuration."""

    subscription_id: str = ""
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    resource_group: str = ""


@dataclass
class CloudInstance:
    """Represents a cloud compute instance."""

    id: str
    name: str
    provider: CloudProvider
    instance_type: str = ""
    state: str = ""
    public_ip: str = ""
    private_ip: str = ""
    region: str = ""
    zone: str = ""
    created_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class CloudBucket:
    """Represents a cloud storage bucket."""

    name: str
    provider: CloudProvider
    region: str = ""
    created_at: Optional[datetime] = None
    public: bool = False


@dataclass
class CloudObject:
    """Represents an object in cloud storage."""

    key: str
    bucket: str
    size: int = 0
    last_modified: Optional[datetime] = None
    content_type: str = ""
    etag: str = ""


class CloudIntegration:
    """
    Unified integration for cloud providers.

    Provides a consistent interface for AWS, GCP, and Azure.

    Example:
        # AWS
        aws = CloudIntegration(CloudProvider.AWS, AWSConfig(
            access_key_id="...",
            secret_access_key="...",
        ))

        # List EC2 instances
        instances = await aws.list_instances()

        # Upload to S3
        await aws.upload_file("my-bucket", "data.csv", "/path/to/file.csv")
    """

    def __init__(
        self,
        provider: CloudProvider,
        config: Union[AWSConfig, GCPConfig, AzureConfig],
    ):
        """Initialize cloud integration."""
        self.provider = provider
        self.config = config
        self._clients: Dict[str, Any] = {}

    # AWS Methods

    def _get_aws_client(self, service: str):
        """Get AWS boto3 client."""
        if service not in self._clients:
            try:
                import boto3

                if isinstance(self.config, AWSConfig):
                    if self.config.profile:
                        session = boto3.Session(profile_name=self.config.profile)
                    else:
                        session = boto3.Session(
                            aws_access_key_id=self.config.access_key_id,
                            aws_secret_access_key=self.config.secret_access_key,
                            region_name=self.config.region,
                        )
                    self._clients[service] = session.client(service)
            except ImportError:
                raise ImportError("boto3 not installed. Install with: pip install boto3")

        return self._clients[service]

    async def _list_aws_instances(self) -> List[CloudInstance]:
        """List AWS EC2 instances."""
        loop = asyncio.get_running_loop()
        ec2 = self._get_aws_client("ec2")

        def _list():
            response = ec2.describe_instances()
            instances = []

            for reservation in response.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}

                    instances.append(
                        CloudInstance(
                            id=inst["InstanceId"],
                            name=tags.get("Name", ""),
                            provider=CloudProvider.AWS,
                            instance_type=inst.get("InstanceType", ""),
                            state=inst.get("State", {}).get("Name", ""),
                            public_ip=inst.get("PublicIpAddress", ""),
                            private_ip=inst.get("PrivateIpAddress", ""),
                            region=self.config.region,
                            zone=inst.get("Placement", {}).get("AvailabilityZone", ""),
                            created_at=inst.get("LaunchTime"),
                            tags=tags,
                        )
                    )

            return instances

        return await loop.run_in_executor(None, _list)

    async def _list_aws_buckets(self) -> List[CloudBucket]:
        """List AWS S3 buckets."""
        loop = asyncio.get_running_loop()
        s3 = self._get_aws_client("s3")

        def _list():
            response = s3.list_buckets()
            return [
                CloudBucket(
                    name=bucket["Name"],
                    provider=CloudProvider.AWS,
                    created_at=bucket.get("CreationDate"),
                )
                for bucket in response.get("Buckets", [])
            ]

        return await loop.run_in_executor(None, _list)

    async def _list_aws_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[CloudObject]:
        """List objects in AWS S3 bucket."""
        loop = asyncio.get_running_loop()
        s3 = self._get_aws_client("s3")

        def _list():
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return [
                CloudObject(
                    key=obj["Key"],
                    bucket=bucket,
                    size=obj.get("Size", 0),
                    last_modified=obj.get("LastModified"),
                    etag=obj.get("ETag", "").strip('"'),
                )
                for obj in response.get("Contents", [])
            ]

        return await loop.run_in_executor(None, _list)

    async def _upload_aws_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Upload file to AWS S3."""
        loop = asyncio.get_running_loop()
        s3 = self._get_aws_client("s3")

        def _upload():
            s3.upload_file(file_path, bucket, key)
            return True

        return await loop.run_in_executor(None, _upload)

    async def _download_aws_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Download file from AWS S3."""
        loop = asyncio.get_running_loop()
        s3 = self._get_aws_client("s3")

        def _download():
            s3.download_file(bucket, key, file_path)
            return True

        return await loop.run_in_executor(None, _download)

    # GCP Methods

    def _get_gcp_client(self, service: str):
        """Get GCP client."""
        if service not in self._clients:
            try:
                if service == "storage":
                    from google.cloud import storage

                    if isinstance(self.config, GCPConfig) and self.config.credentials_file:
                        self._clients[service] = storage.Client.from_service_account_json(
                            self.config.credentials_file
                        )
                    else:
                        self._clients[service] = storage.Client()

                elif service == "compute":
                    from google.cloud import compute_v1

                    if isinstance(self.config, GCPConfig) and self.config.credentials_file:
                        self._clients[service] = (
                            compute_v1.InstancesClient.from_service_account_json(
                                self.config.credentials_file
                            )
                        )
                    else:
                        self._clients[service] = compute_v1.InstancesClient()

            except ImportError:
                raise ImportError(
                    "Google Cloud SDK not installed. Install with: "
                    "pip install google-cloud-storage google-cloud-compute"
                )

        return self._clients[service]

    async def _list_gcp_instances(self) -> List[CloudInstance]:
        """List GCP Compute Engine instances."""
        loop = asyncio.get_running_loop()

        def _list():
            from google.cloud import compute_v1

            client = self._get_gcp_client("compute")
            config = self.config

            if not isinstance(config, GCPConfig):
                return []

            request = compute_v1.AggregatedListInstancesRequest(
                project=config.project_id,
            )

            instances = []
            for zone, response in client.aggregated_list(request=request):
                if response.instances:
                    for inst in response.instances:
                        # Extract zone name
                        zone_name = zone.split("/")[-1] if "/" in zone else zone

                        instances.append(
                            CloudInstance(
                                id=str(inst.id),
                                name=inst.name,
                                provider=CloudProvider.GCP,
                                instance_type=inst.machine_type.split("/")[-1],
                                state=inst.status,
                                public_ip=(
                                    inst.network_interfaces[0].access_configs[0].nat_i_p
                                    if inst.network_interfaces
                                    and inst.network_interfaces[0].access_configs
                                    else ""
                                ),
                                private_ip=(
                                    inst.network_interfaces[0].network_i_p
                                    if inst.network_interfaces
                                    else ""
                                ),
                                region=config.region,
                                zone=zone_name,
                                tags=dict(inst.labels) if inst.labels else {},
                            )
                        )

            return instances

        return await loop.run_in_executor(None, _list)

    async def _list_gcp_buckets(self) -> List[CloudBucket]:
        """List GCP Cloud Storage buckets."""
        loop = asyncio.get_running_loop()
        storage = self._get_gcp_client("storage")

        def _list():
            buckets = storage.list_buckets()
            return [
                CloudBucket(
                    name=bucket.name,
                    provider=CloudProvider.GCP,
                    region=bucket.location,
                    created_at=bucket.time_created,
                )
                for bucket in buckets
            ]

        return await loop.run_in_executor(None, _list)

    async def _list_gcp_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[CloudObject]:
        """List objects in GCP bucket."""
        loop = asyncio.get_running_loop()
        storage = self._get_gcp_client("storage")

        def _list():
            bucket_obj = storage.bucket(bucket)
            blobs = bucket_obj.list_blobs(prefix=prefix, max_results=max_results)

            return [
                CloudObject(
                    key=blob.name,
                    bucket=bucket,
                    size=blob.size or 0,
                    last_modified=blob.updated,
                    content_type=blob.content_type or "",
                    etag=blob.etag or "",
                )
                for blob in blobs
            ]

        return await loop.run_in_executor(None, _list)

    async def _upload_gcp_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Upload file to GCP Cloud Storage."""
        loop = asyncio.get_running_loop()
        storage = self._get_gcp_client("storage")

        def _upload():
            bucket_obj = storage.bucket(bucket)
            blob = bucket_obj.blob(key)
            blob.upload_from_filename(file_path)
            return True

        return await loop.run_in_executor(None, _upload)

    async def _download_gcp_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Download file from GCP Cloud Storage."""
        loop = asyncio.get_running_loop()
        storage = self._get_gcp_client("storage")

        def _download():
            bucket_obj = storage.bucket(bucket)
            blob = bucket_obj.blob(key)
            blob.download_to_filename(file_path)
            return True

        return await loop.run_in_executor(None, _download)

    # Azure Methods

    def _get_azure_credential(self):
        """Get Azure credential."""
        try:
            from azure.identity import ClientSecretCredential

            if isinstance(self.config, AzureConfig):
                return ClientSecretCredential(
                    tenant_id=self.config.tenant_id,
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                )
        except ImportError:
            raise ImportError(
                "Azure SDK not installed. Install with: "
                "pip install azure-identity azure-mgmt-compute azure-storage-blob"
            )

    async def _list_azure_instances(self) -> List[CloudInstance]:
        """List Azure VMs."""
        loop = asyncio.get_running_loop()

        def _list():
            from azure.mgmt.compute import ComputeManagementClient

            config = self.config
            if not isinstance(config, AzureConfig):
                return []

            credential = self._get_azure_credential()
            client = ComputeManagementClient(credential, config.subscription_id)

            instances = []
            for vm in client.virtual_machines.list_all():
                instances.append(
                    CloudInstance(
                        id=vm.id,
                        name=vm.name,
                        provider=CloudProvider.AZURE,
                        instance_type=vm.hardware_profile.vm_size,
                        state=vm.provisioning_state,
                        region=vm.location,
                        tags=vm.tags or {},
                    )
                )

            return instances

        return await loop.run_in_executor(None, _list)

    # Unified Methods

    async def list_instances(self) -> List[CloudInstance]:
        """List compute instances."""
        if self.provider == CloudProvider.AWS:
            return await self._list_aws_instances()
        elif self.provider == CloudProvider.GCP:
            return await self._list_gcp_instances()
        elif self.provider == CloudProvider.AZURE:
            return await self._list_azure_instances()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def list_buckets(self) -> List[CloudBucket]:
        """List storage buckets."""
        if self.provider == CloudProvider.AWS:
            return await self._list_aws_buckets()
        elif self.provider == CloudProvider.GCP:
            return await self._list_gcp_buckets()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_results: int = 1000,
    ) -> List[CloudObject]:
        """List objects in a bucket."""
        if self.provider == CloudProvider.AWS:
            return await self._list_aws_objects(bucket, prefix, max_results)
        elif self.provider == CloudProvider.GCP:
            return await self._list_gcp_objects(bucket, prefix, max_results)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def upload_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Upload a file to cloud storage."""
        if self.provider == CloudProvider.AWS:
            return await self._upload_aws_file(bucket, key, file_path)
        elif self.provider == CloudProvider.GCP:
            return await self._upload_gcp_file(bucket, key, file_path)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def download_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> bool:
        """Download a file from cloud storage."""
        if self.provider == CloudProvider.AWS:
            return await self._download_aws_file(bucket, key, file_path)
        elif self.provider == CloudProvider.GCP:
            return await self._download_gcp_file(bucket, key, file_path)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def get_cost_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get cost/billing data.

        Currently only supported for AWS.
        """
        if self.provider == CloudProvider.AWS:
            loop = asyncio.get_running_loop()
            ce = self._get_aws_client("ce")

            def _get_cost():
                response = ce.get_cost_and_usage(
                    TimePeriod={
                        "Start": start_date.strftime("%Y-%m-%d"),
                        "End": end_date.strftime("%Y-%m-%d"),
                    },
                    Granularity="DAILY",
                    Metrics=["UnblendedCost"],
                )
                return response

            return await loop.run_in_executor(None, _get_cost)
        else:
            raise NotImplementedError(f"Cost data not implemented for {self.provider}")
