"""
MinIO OSS 服务 - 多媒体文件存储（思维导图、代码截图、头像等）
"""

import logging
import io
from typing import Optional, BinaryIO
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# 全局客户端
_minio_client: Optional[Minio] = None

# 存储桶
BUCKETS = {
    "avatars": "用户头像",
    "mindmaps": "思维导图图片",
    "code_screenshots": "代码截图",
    "exports": "学习报告导出",
    "uploads": "用户上传文件",
}


async def init_minio(
    endpoint: str = "localhost:9000",
    access_key: str = "minioadmin",
    secret_key: str = "minioadmin",
    secure: bool = False,
) -> Minio:
    """初始化 MinIO 连接 + 创建存储桶"""
    global _minio_client

    logger.info(f"[MinIO] 连接: {endpoint}")
    _minio_client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )

    # 创建所有桶
    for bucket_name in BUCKETS:
        try:
            if not _minio_client.bucket_exists(bucket_name):
                _minio_client.make_bucket(bucket_name)
                logger.info(f"[MinIO] 创建存储桶: {bucket_name} ({BUCKETS[bucket_name]})")
            else:
                logger.debug(f"[MinIO] 存储桶已存在: {bucket_name}")
        except S3Error as e:
            if e.code != "BucketAlreadyOwnedByYou":
                logger.error(f"[MinIO] 创建存储桶失败 {bucket_name}: {e}")

    logger.info("[MinIO] 连接成功")
    return _minio_client


async def close_minio():
    """关闭 MinIO 连接"""
    global _minio_client
    _minio_client = None
    logger.info("[MinIO] 连接已释放")


def get_minio() -> Optional[Minio]:
    return _minio_client


# ===== 文件操作 =====

async def upload_file(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> Optional[str]:
    """
    上传文件到 MinIO

    Args:
        bucket: 存储桶名（avatars/mindmaps/code_screenshots/exports/uploads）
        object_name: 对象名（如 user_123/mindmap_20260524.png）
        data: 文件字节数据
        content_type: MIME 类型

    Returns:
        对象的 URL 路径，失败返回 None
    """
    client = get_minio()
    if not client:
        logger.warning("[MinIO] 客户端未初始化，跳过上传")
        return None

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"[MinIO] 上传成功: {bucket}/{object_name} ({len(data)} bytes)")
        return f"{bucket}/{object_name}"
    except S3Error as e:
        logger.error(f"[MinIO] 上传失败: {e}")
        return None


async def upload_text(
    bucket: str,
    object_name: str,
    text: str,
    content_type: str = "text/plain",
) -> Optional[str]:
    """上传文本内容到 MinIO"""
    return await upload_file(bucket, object_name, text.encode("utf-8"), content_type)


async def get_file(bucket: str, object_name: str) -> Optional[bytes]:
    """从 MinIO 下载文件"""
    client = get_minio()
    if not client:
        return None

    try:
        response = client.get_object(bucket_name=bucket, object_name=object_name)
        data = response.read()
        response.close()
        response.release_conn()
        logger.info(f"[MinIO] 下载成功: {bucket}/{object_name}")
        return data
    except S3Error as e:
        logger.warning(f"[MinIO] 下载失败 {bucket}/{object_name}: {e}")
        return None


async def get_text(bucket: str, object_name: str) -> Optional[str]:
    """从 MinIO 下载文本"""
    data = await get_file(bucket, object_name)
    return data.decode("utf-8") if data else None


async def get_presigned_url(
    bucket: str,
    object_name: str,
    expires_hours: int = 24,
) -> Optional[str]:
    """
    生成预签名 URL（临时访问链接）

    Args:
        bucket: 存储桶名
        object_name: 对象名
        expires_hours: 过期时间（小时）

    Returns:
        临时 HTTPS/HTTP 链接
    """
    client = get_minio()
    if not client:
        return None

    try:
        url = client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(hours=expires_hours),
        )
        return url
    except S3Error as e:
        logger.warning(f"[MinIO] 生成URL失败 {bucket}/{object_name}: {e}")
        return None


async def delete_file(bucket: str, object_name: str) -> bool:
    """删除 MinIO 中的文件"""
    client = get_minio()
    if not client:
        return False

    try:
        client.remove_object(bucket_name=bucket, object_name=object_name)
        logger.info(f"[MinIO] 已删除: {bucket}/{object_name}")
        return True
    except S3Error as e:
        logger.warning(f"[MinIO] 删除失败 {bucket}/{object_name}: {e}")
        return False


async def list_files(bucket: str, prefix: str = "", limit: int = 100) -> list[dict]:
    """列出存储桶中的文件"""
    client = get_minio()
    if not client:
        return []

    try:
        objects = client.list_objects(
            bucket_name=bucket,
            prefix=prefix,
            recursive=True,
        )
        result = []
        for i, obj in enumerate(objects):
            if i >= limit:
                break
            result.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": str(obj.last_modified),
            })
        return result
    except S3Error as e:
        logger.warning(f"[MinIO] 列表失败 {bucket}: {e}")
        return []