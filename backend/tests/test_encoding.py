"""验证 akshare 原始返回数据的中文编码"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import akshare as ak

print("=" * 50)
print("验证 1: stock_zt_pool_em 中文返回")
print("=" * 50)
try:
    df = ak.stock_zt_pool_em(date="20260824")
    print(f"数据类型: {type(df)}")
    print(f"列名: {list(df.columns)}")
    print(f"\n前3行原始数据:")
    print(df.head(3).to_string())
    print(f"\n第1行名称字段: repr={df.iloc[0]['名称']!r}")
except Exception as e:
    print(f"失败: {e}")

print("\n" + "=" * 50)
print("验证 2: stock_board_industry_name_em 中文返回")
print("=" * 50)
try:
    df2 = ak.stock_board_industry_name_em()
    print(f"前3行原始数据:")
    print(df2.head(3).to_string())
    print(f"\n第1行板块名称: repr={df2.iloc[0]['板块名称']!r}")
except Exception as e:
    print(f"失败: {e}")

print("\n" + "=" * 50)
print("系统编码信息")
print("=" * 50)
print(f"sys.getdefaultencoding(): {sys.getdefaultencoding()}")
print(f"sys.stdout.encoding: {sys.stdout.encoding}")
import locale
print(f"locale.getpreferredencoding(): {locale.getpreferredencoding()}")
