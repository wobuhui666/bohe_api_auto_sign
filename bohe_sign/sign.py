"""签到逻辑实现模块 - 抽奖 + CDK 兑换"""

import logging
from http import HTTPStatus
from typing import Any, Dict, Optional

from curl_cffi import requests

from store.token import load_tokens, get_newapi_config
from store.log import add_sign_log, get_sign_stats

# 设置日志
logger = logging.getLogger(__name__)

IMPERSONATE = "chrome"

# API 端点
LOTTERY_API = "https://qd.x666.me/api/lottery/spin"  # 抽奖 API
USER_INFO_API = "https://qd.x666.me/api/user/info"   # 用户信息 API
TOPUP_API = "https://x666.me/api/user/topup"         # NewAPI 兑换 API


async def do_lottery() -> Dict[str, Any]:
    """执行抽奖获取 CDK
    
    Returns:
        抽奖结果字典，包含 success, message, cdk, quota 等字段
    """
    tokens = load_tokens()
    bohe_token = tokens.get("bohe_sign_token")
    
    if not bohe_token:
        return {
            "success": False,
            "message": "未找到有效的薄荷 Token，请先设置 Linux.do Token 并刷新",
            "cdk": None
        }
    
    try:
        logger.info(f"正在请求抽奖 API: {LOTTERY_API}")
        
        async with requests.AsyncSession() as session:
            r = await session.post(
                LOTTERY_API,
                headers={
                    "Authorization": f"Bearer {bohe_token}",
                    "Content-Type": "application/json"
                },
                json={},
                impersonate=IMPERSONATE
            )
            
            logger.info(f"抽奖 API 响应状态码: {r.status_code}")
            
            if r.status_code == HTTPStatus.OK:
                result = r.json()
                logger.debug(f"抽奖响应: {result}")
                
                if result.get("success"):
                    data = result.get("data", {})
                    cdk = data.get("cdk")
                    quota = data.get("quota", 0)
                    times = data.get("times", 0)
                    label = data.get("label", "")
                    
                    return {
                        "success": True,
                        "message": f"抽奖成功！获得 {label}，额度 {quota}",
                        "cdk": cdk,
                        "quota": quota,
                        "times": times,
                        "label": label
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get("message", "抽奖失败"),
                        "cdk": None
                    }
            else:
                error_body = ""
                try:
                    error_body = r.text[:200]
                except:
                    pass
                logger.error(f"抽奖失败 - 状态码: {r.status_code}, 响应: {error_body}")
                return {
                    "success": False,
                    "message": f"抽奖请求失败，HTTP 状态码: {r.status_code}",
                    "cdk": None
                }
                
    except Exception as e:
        logger.error(f"抽奖请求异常: {e}")
        return {
            "success": False,
            "message": f"抽奖请求异常: {str(e)}",
            "cdk": None
        }


async def do_topup(cdk: str) -> Dict[str, Any]:
    """使用 CDK 在 NewAPI 兑换额度
    
    Args:
        cdk: 兑换码
        
    Returns:
        兑换结果字典
    """
    newapi_config = get_newapi_config()
    session_cookie = newapi_config.get("session", "")
    user_id = newapi_config.get("user_id", "")
    
    if not session_cookie or not user_id:
        return {
            "success": False,
            "message": "未配置 NewAPI 认证信息，请先设置 NewAPI Session 和 User ID"
        }
    
    try:
        logger.info(f"正在请求兑换 API: {TOPUP_API}")
        logger.debug(f"CDK: {cdk[:8]}..., User ID: {user_id}")
        
        async with requests.AsyncSession() as session:
            r = await session.post(
                TOPUP_API,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*",
                    "New-API-User": user_id,
                    "Cookie": f"session={session_cookie}"
                },
                json={"key": cdk},
                impersonate=IMPERSONATE
            )
            
            logger.info(f"兑换 API 响应状态码: {r.status_code}")
            
            if r.status_code == HTTPStatus.OK:
                result = r.json()
                logger.debug(f"兑换响应: {result}")
                
                if result.get("success"):
                    quota = result.get("data", 0)
                    return {
                        "success": True,
                        "message": f"兑换成功！获得额度: {quota}",
                        "quota": quota
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get("message", "兑换失败")
                    }
            else:
                error_body = ""
                try:
                    error_body = r.text[:200]
                except:
                    pass
                logger.error(f"兑换失败 - 状态码: {r.status_code}, 响应: {error_body}")
                return {
                    "success": False,
                    "message": f"兑换请求失败，HTTP 状态码: {r.status_code}"
                }
                
    except Exception as e:
        logger.error(f"兑换请求异常: {e}")
        return {
            "success": False,
            "message": f"兑换请求异常: {str(e)}"
        }


async def do_sign(trigger: str = "manual") -> Dict[str, Any]:
    """执行完整签到流程：抽奖 + 兑换
    
    Args:
        trigger: 触发方式 (manual/scheduled)
        
    Returns:
        签到结果字典，包含 success, message, data 字段
    """
    # 步骤1: 抽奖获取 CDK
    lottery_result = await do_lottery()
    
    if not lottery_result.get("success"):
        error_msg = lottery_result.get("message", "抽奖失败")
        add_sign_log(
            status="failed",
            message=f"抽奖失败: {error_msg}",
            trigger=trigger
        )
        return {
            "success": False,
            "message": error_msg
        }
    
    cdk = lottery_result.get("cdk")
    if not cdk:
        error_msg = "抽奖成功但未获得 CDK"
        add_sign_log(
            status="failed",
            message=error_msg,
            trigger=trigger
        )
        return {
            "success": False,
            "message": error_msg
        }
    
    lottery_msg = lottery_result.get("message", "")
    quota_from_lottery = lottery_result.get("quota", 0)
    
    # 步骤2: 使用 CDK 兑换额度
    topup_result = await do_topup(cdk)
    
    if not topup_result.get("success"):
        # 抽奖成功但兑换失败
        error_msg = topup_result.get("message", "兑换失败")
        add_sign_log(
            status="failed",
            message=f"抽奖成功(CDK: {cdk[:8]}...)，但兑换失败: {error_msg}",
            trigger=trigger
        )
        return {
            "success": False,
            "message": f"抽奖成功，但兑换失败: {error_msg}",
            "data": {
                "cdk": cdk,
                "lottery_quota": quota_from_lottery
            }
        }
    
    # 完全成功
    final_quota = topup_result.get("quota", quota_from_lottery)
    success_msg = f"签到成功！{lottery_msg}，已兑换额度: {final_quota}"
    
    add_sign_log(
        status="success",
        message=success_msg,
        trigger=trigger
    )
    
    return {
        "success": True,
        "message": success_msg,
        "data": {
            "cdk": cdk,
            "quota": final_quota,
            "times": lottery_result.get("times", 0),
            "label": lottery_result.get("label", "")
        }
    }


async def get_sign_status() -> Dict[str, Any]:
    """获取签到状态
    
    Returns:
        签到状态字典，包含 signed_today, last_sign_time, continuous_days, total_signs
    """
    # 从本地日志获取基础统计
    stats = get_sign_stats()
    
    # 尝试从 API 获取更多信息（如果 token 有效）
    tokens = load_tokens()
    bohe_token = tokens.get("bohe_sign_token")
    
    if bohe_token:
        try:
            async with requests.AsyncSession() as session:
                r = await session.post(
                    USER_INFO_API,
                    headers={"Authorization": f"Bearer {bohe_token}"},
                    json={},
                    impersonate=IMPERSONATE
                )
                
                if r.status_code == HTTPStatus.OK:
                    result = r.json()
                    if result.get("success"):
                        user_data = result.get("data", {})
                        # 如果 API 返回了更准确的数据，可以补充
                        if "continuous_days" in user_data:
                            stats["continuous_days"] = user_data["continuous_days"]
                        if "total_signs" in user_data:
                            stats["total_signs"] = user_data["total_signs"]
        except Exception:
            # API 调用失败，使用本地统计数据
            pass
    
    return stats