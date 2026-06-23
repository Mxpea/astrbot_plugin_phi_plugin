"""
Phi-Plugin for AstrBot
Ported from phi-plugin-main (Yunzai-Bot V3 plugin)

This plugin provides Phigros game information query functionality including:
- B30/B19 score queries
- Song information lookup
- User statistics
- And more
"""

import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image, At

from .lib import PhigrosUser, SaveManager
from .model import get_info_instance, SongsInfo, Chart


class PhiPlugin(Star):
    """Phigros game information query plugin."""
    
    def __init__(self, context: Context, config: dict):
        """Initialize plugin.
        
        Args:
            context: AstrBot context
            config: Plugin configuration
        """
        super().__init__(context)
        self.config = config
        
        # Get plugin directory
        self.plugin_dir = Path(__file__).parent
        
        # Resources path
        self.resources_path = self.plugin_dir / 'resources'
        
        # Initialize song info manager
        self.get_info = get_info_instance(str(self.resources_path))
        
        # User data storage
        self.user_data_path = self.plugin_dir / 'data'
        self.user_data_path.mkdir(exist_ok=True)
        
        # Initialize state
        self._initialized = False
    
    async def initialize(self):
        """Initialize plugin data."""
        if self._initialized:
            return
        
        logger.info("[phi-plugin] 正在初始化...")
        
        # Initialize song info
        await self.get_info.init()
        
        self._initialized = True
        logger.info("[phi-plugin] 初始化完成")
    
    async def terminate(self):
        """Clean up when plugin is unloaded."""
        logger.info("[phi-plugin] 插件已卸载")
    
    # ==================== Helper Methods ====================
    
    def _get_user_token(self, user_id: str) -> Optional[str]:
        """Get user's session token.
        
        Args:
            user_id: User ID
            
        Returns:
            Session token or None
        """
        token_file = self.user_data_path / f"{user_id}.json"
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('session_token')
        return None
    
    def _save_user_token(self, user_id: str, session_token: str) -> None:
        """Save user's session token.
        
        Args:
            user_id: User ID
            session_token: Session token to save
        """
        token_file = self.user_data_path / f"{user_id}.json"
        data = {}
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        data['session_token'] = session_token
        
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _delete_user_token(self, user_id: str) -> bool:
        """Delete user's session token.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        token_file = self.user_data_path / f"{user_id}.json"
        if token_file.exists():
            token_file.unlink()
            return True
        return False
    
    async def _get_user_save(self, user_id: str) -> Optional[PhigrosUser]:
        """Get user's save data.
        
        Args:
            user_id: User ID
            
        Returns:
            PhigrosUser or None
        """
        token = self._get_user_token(user_id)
        if not token:
            return None
        
        try:
            user = PhigrosUser(session=token)
            await user.get_save_info()
            await user.build_record()
            return user
        except Exception as e:
            logger.error(f"[phi-plugin] 获取存档失败: {e}")
            return None
    
    # ==================== Command Handlers ====================
    
    @filter.command("phihelp")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """
🎮 Phi-Plugin 帮助

【基础指令】
/phihelp - 显示此帮助
/phi bind <sessionToken> - 绑定sessionToken
/phi unbind - 解绑sessionToken
/phi update - 更新存档

【查询指令】
/phi b30 - 查询B30成绩
/phi score <曲名> - 查询单曲成绩
/phi info - 查询个人信息
/phi suggest - 获取推分建议

【曲目信息】
/phi song <曲名> - 查询曲目图鉴
/phi chart <曲名> [难度] - 查询谱面信息
/phi search <条件> <值> - 检索曲目

【娱乐功能】
/phi guess - 猜曲绘
/phi rand [定数] [难度] - 随机曲目
/phi jrrp - 今日人品

【管理指令】
/phi set <功能> <值> - 修改设置
/phi backup - 备份存档
"""
        yield event.plain_result(help_text)
    
    @filter.command("bind")
    async def bind_command(self, event: AstrMessageEvent, token: str = None):
        """绑定sessionToken
        
        Args:
            token: Session token to bind
        """
        user_id = event.get_sender_id()
        
        if not token:
            yield event.plain_result(
                "请提供sessionToken！\n"
                "格式：/phi bind <sessionToken>\n"
                "获取方法：/phi tk help"
            )
            return
        
        # Validate token format
        import re
        if not re.match(r'^[a-z0-9A-Z]{25}$', token):
            yield event.plain_result("sessionToken格式错误！应为25位字母数字组合。")
            return
        
        # Try to get save info to validate token
        try:
            user = PhigrosUser(session=token)
            await user.get_save_info()
            
            # Save token
            self._save_user_token(user_id, token)
            
            yield event.plain_result(
                f"绑定成功！\n"
                f"玩家ID: {user.get_player_id()}\n"
                f"RKS: {user.get_rks():.2f}"
            )
        except Exception as e:
            yield event.plain_result(f"绑定失败：{str(e)}")
    
    @filter.command("unbind")
    async def unbind_command(self, event: AstrMessageEvent):
        """解绑sessionToken"""
        user_id = event.get_sender_id()
        
        if self._delete_user_token(user_id):
            yield event.plain_result("已解绑sessionToken！")
        else:
            yield event.plain_result("你还没有绑定sessionToken哦！")
    
    @filter.command("update")
    async def update_command(self, event: AstrMessageEvent):
        """更新存档"""
        user_id = event.get_sender_id()
        
        # Check if user has token
        token = self._get_user_token(user_id)
        if not token:
            yield event.plain_result(
                "请先绑定sessionToken！\n"
                "格式：/phi bind <sessionToken>"
            )
            return
        
        yield event.plain_result("正在更新存档，请稍等...")
        
        try:
            user = await self._get_user_save(user_id)
            if user:
                yield event.plain_result(
                    f"存档更新成功！\n"
                    f"玩家ID: {user.get_player_id()}\n"
                    f"RKS: {user.get_rks():.2f}\n"
                    f"Challenge Mode: {user.get_challenge_mode()}"
                )
            else:
                yield event.plain_result("存档更新失败！请检查sessionToken是否正确。")
        except Exception as e:
            yield event.plain_result(f"更新失败：{str(e)}")
    
    @filter.command("b30")
    async def b30_command(self, event: AstrMessageEvent):
        """查询B30成绩"""
        user_id = event.get_sender_id()
        
        # Get user save
        user = await self._get_user_save(user_id)
        if not user:
            yield event.plain_result(
                "请先绑定sessionToken！\n"
                "格式：/phi bind <sessionToken>"
            )
            return
        
        yield event.plain_result("正在计算B30，请稍等...")
        
        try:
            # Get B19 records
            records = user.game_record.get_rks_records(
                lambda song_id: self.get_info.get_info(song_id)
            )
            
            # Get top 30 (B30 = 3 best + 27 normal)
            b30 = records[:30]
            
            # Format response
            response = f"🎮 B30 成绩查询\n"
            response += f"玩家ID: {user.get_player_id()}\n"
            response += f"RKS: {user.get_rks():.4f}\n"
            response += f"Challenge Mode: {user.get_challenge_mode()[0]}{user.get_challenge_mode()[1]}\n\n"
            
            for i, record in enumerate(b30, 1):
                song_info = self.get_info.get_info(record['song_id'])
                song_name = song_info.song if song_info else record['song_id']
                response += f"#{i}: {song_name} [{record['level']}]\n"
                response += f"   分数: {record['record'].score} | ACC: {record['record'].acc:.2f}% | RKS: {record['rks']:.2f}\n"
            
            yield event.plain_result(response)
        except Exception as e:
            yield event.plain_result(f"查询失败：{str(e)}")
    
    @filter.command("info")
    async def info_command(self, event: AstrMessageEvent):
        """查询个人信息"""
        user_id = event.get_sender_id()
        
        user = await self._get_user_save(user_id)
        if not user:
            yield event.plain_result(
                "请先绑定sessionToken！\n"
                "格式：/phi bind <sessionToken>"
            )
            return
        
        try:
            challenge_mode, challenge_rank = user.get_challenge_mode()
            money_str = user.format_money()
            
            response = f"🎮 个人信息\n"
            response += f"玩家ID: {user.get_player_id()}\n"
            response += f"RKS: {user.get_rks():.4f}\n"
            response += f"Challenge Mode: {challenge_mode}{challenge_rank}\n"
            response += f"数据: {money_str}\n"
            
            yield event.plain_result(response)
        except Exception as e:
            yield event.plain_result(f"查询失败：{str(e)}")
    
    @filter.command("song")
    async def song_command(self, event: AstrMessageEvent, song_name: str = None):
        """查询曲目信息
        
        Args:
            song_name: Song name to query
        """
        if not song_name:
            yield event.plain_result("请指定曲名！\n格式：/phi song <曲名>")
            return
        
        # Search for song
        song_ids = self.get_info.fuzzy_search(song_name)
        
        if not song_ids:
            yield event.plain_result(f"未找到曲目：{song_name}")
            return
        
        # Get first match
        song_info = self.get_info.get_info(song_ids[0])
        
        if not song_info:
            yield event.plain_result(f"未找到曲目信息：{song_name}")
            return
        
        # Format response
        response = f"🎵 曲目信息\n"
        response += f"曲名: {song_info.song}\n"
        response += f"ID: {song_info.id}\n"
        response += f"章节: {song_info.chapter}\n"
        response += f"作曲: {song_info.composer}\n"
        response += f"画师: {song_info.illustrator}\n"
        response += f"BPM: {song_info.bpm}\n"
        response += f"时长: {song_info.length}\n\n"
        
        response += "📊 谱面信息\n"
        for level, chart in song_info.chart.items():
            response += f"[{level}] 定数: {chart.difficulty:.1f}"
            if chart.combo:
                response += f" | 物量: {chart.combo}"
            if chart.charter:
                response += f" | 谱师: {chart.charter}"
            response += "\n"
        
        yield event.plain_result(response)
