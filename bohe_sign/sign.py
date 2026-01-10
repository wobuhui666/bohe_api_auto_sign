"""签到逻辑实现模块"""

from http import HTTPStatus
from typing import Any, Dict

from curl_cffi import requests

from store.token import load_tokens
from store.log import add_sign_log, get_sign_stats

IMPERSONATE = "chrome"
SIGN_API = "https://up.x666.me/api/user/sign"
USER_INFO_API = "https://up.x666.me/api/user/info"
SPIN_API = "https://up.x666.me/api/checkin/spin"


async def do_sign(trigger: str = "manual") -> Dict[str, Any]:
    """执行签到操作
    
    Args:
        trigger: 触发方式 (manual/scheduled)
        
    Returns:
        签到结果字典，包含 success, message, data 字段
    """
    tokens = load_tokens()
    bohe_token = tokens.get("bohe_sign_token")
    
    if not bohe_token:
        error_msg = "未找到有效的薄荷 Token，请先设置 Linux.do Token 并刷新"
        add_sign_log(
            status="failed",
            message=error_msg,
            trigger=trigger
        )
        return {
            "success": False,
            "message": error_msg
        }
    
    try:
        async with requests.AsyncSession() as session:
            r = await session.post(
                SIGN_API,
                headers={"Authorization": f"Bearer {bohe_token}"},
                json={},
                impersonate=IMPERSONATE
            )
            
            if r.status_code == HTTPStatus.OK:
                result = r.json()
                
                if result.get("success"):
                    # 签到成功
                    message = result.get("message", "签到成功")
                    add_sign_log(
                        status="success",
                        message=message,
                        trigger=trigger
                    )
                    return {
                        "success": True,
                        "message": message,
                        "data": result.get("data", {})
                    }
                else:
                    # API 返回失败
                    message = result.get("message", "签到失败")
                    add_sign_log(
                        status="failed",
                        message=message,
                        trigger=trigger
                    )
                    return {
                        "success": False,
                        "message": message
                    }
            else:
                error_msg = f"签到请求失败，HTTP 状态码: {r.status_code}"
                add_sign_log(
                    status="failed",
                    message=error_msg,
                    trigger=trigger
                )
                return {
                    "success": False,
                    "message": error_msg
                }
                
    except Exception as e:
        error_msg = f"签到请求异常: {str(e)}"
        add_sign_log(
            status="failed",
            message=error_msg,
            trigger=trigger
        )
        return {
            "success": False,
            "message": error_msg
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


async def spin(token: str) -> Dict[str, Any]:
    """执行转盘抽奖

    Args:
        token: 用户薄荷 Token

    Returns:
        抽奖结果字典
    """
    if not token:
        return {"success": False, "message": "Token not provided"}

    try:
        async with requests.AsyncSession() as session:
            r = await session.post(
                SPIN_API,
                headers={"Authorization": f"Bearer {token}"},
                json={},
                impersonate=IMPERSONATE,
            )

            if r.status_code == HTTPStatus.OK:
                result = r.json()
                return {
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "data": result.get("data", {}),
                }
            else:
                return {
                    "success": False,
                    "message": f"Spin request failed, HTTP status code: {r.status_code}",
                }

    except Exception as e:
        return {"success": False, "message": f"Spin request exception: {str(e)}"}