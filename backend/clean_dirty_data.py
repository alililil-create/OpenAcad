"""清理数据库中 document.content 含题库 JSON 的脏数据"""
import sqlite3
import json

DB_PATH = "ml_learning.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

dirty = []
for row in cur.execute(
    "SELECT id, user_id, chapter_id, is_current, LENGTH(content), content "
    "FROM learning_materials ORDER BY id ASC"
):
    mid, uid, ch, is_cur, length, content = row
    is_dirty = False
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            doc = obj.get("document", {})
            if isinstance(doc, dict):
                dc = doc.get("content", "")
                if isinstance(dc, str):
                    s = dc.strip()
                    # 文档内容以 JSON 数组开头
                    if s.startswith("[") and '"id"' in s[:200]:
                        is_dirty = True
                    # 文档中含题库特征字段
                    elif '"question":' in s[:5000] and '"explanation":' in s[:5000]:
                        is_dirty = True
    except (json.JSONDecodeError, TypeError):
        pass

    if is_dirty:
        dirty.append(mid)
        print(f"  [脏] id={mid} user={uid} chapter={ch} is_current={is_cur} len={length}")

print(f"\n共 {len(dirty)} 条脏数据")

if dirty:
    print("开始删除...")
    for mid in dirty:
        cur.execute("DELETE FROM learning_materials WHERE id = ?", (mid,))
    conn.commit()
    print(f"已删除 {len(dirty)} 条")
else:
    print("没有脏数据")

cur.execute("SELECT COUNT(*) FROM learning_materials")
print(f"剩余: {cur.fetchone()[0]} 条")

conn.close()
print("\n[OK] 清理完成")
