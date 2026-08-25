"""
阶段 2.5 风险预警详情 - 后端接口验证

验证 /api/risk 返回的 triggers 包含增强字段：
- current_value: 当前值
- yellow_threshold: 黄线阈值
- red_threshold: 红线阈值
"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8003"

def test_risk_triggers_enhanced_fields():
    """验证 /api/risk 接口返回的 triggers 包含增强字段"""
    print("\n========== 测试：风险接口增强字段 ==========")
    
    url = f"{BASE_URL}/api/risk"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        print(f"✓ 请求成功: {url}")
        print(f"  交易日: {data.get('trade_date')}")
        print(f"  风险等级: {data.get('level')} - {data.get('label')}")
        print(f"  触发项数量: {len(data.get('triggers', []))}")
        
        triggers = data.get('triggers', [])
        if len(triggers) == 0:
            print("  ⚠️ 当前无触发项（市场平稳）")
            return True
        
        for i, t in enumerate(triggers, 1):
            print(f"\n  触发项 {i}:")
            print(f"    维度: {t.get('dimension')}")
            print(f"    等级: {t.get('level')}")
            print(f"    明细: {t.get('detail')}")
            
            required_fields = ['current_value', 'yellow_threshold', 'red_threshold']
            for field in required_fields:
                if field not in t:
                    print(f"    ✗ 缺少字段: {field}")
                    return False
                print(f"    {field}: {t[field]}")
            
            if not isinstance(t['current_value'], (int, float)):
                print(f"    ✗ current_value 类型错误: {type(t['current_value'])}")
                return False
            
            if not isinstance(t['yellow_threshold'], (int, float)):
                print(f"    ✗ yellow_threshold 类型错误: {type(t['yellow_threshold'])}")
                return False
            
            if not isinstance(t['red_threshold'], (int, float)):
                print(f"    ✗ red_threshold 类型错误: {type(t['red_threshold'])}")
                return False
        
        print(f"\n✓ 所有触发项均包含增强字段，类型正确")
        return True
    
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP 错误: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def main():
    print("阶段 2.5 风险预警详情 - 后端接口验证")
    print("=" * 50)
    
    result = test_risk_triggers_enhanced_fields()
    
    print("\n" + "=" * 50)
    if result:
        print("✓ 验证通过")
    else:
        print("✗ 验证失败")
    
    return 0 if result else 1

if __name__ == "__main__":
    exit(main())
