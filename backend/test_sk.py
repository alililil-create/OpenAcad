import base64, hashlib

SK = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="

print("=" * 60)
print("分析 Secret Access Key")
print("=" * 60)

print(f"\n原始值: {SK}")
print(f"长度:   {len(SK)}")

try:
    decoded = base64.b64decode(SK)
    print(f"\nBase64解码后: {decoded}")
    print(f"解码后长度:    {len(decoded)}")
    print(f"解码后(hex):   {decoded.hex()}")
    
    # 尝试作为 UTF-8 解码
    try:
        text = decoded.decode('utf-8')
        print(f"\nUTF-8文本: {text}")
    except:
        print("\n不是有效的UTF-8文本")
        
except Exception as e:
    print(f"\n解码失败: {e}")

# SHA256 哈希
print(f"\nSHA256: {hashlib.sha256(SK.encode()).hexdigest()}")
