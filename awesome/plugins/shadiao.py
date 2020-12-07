import os
import random
import re
import time

import aiocqhttp.event
import aiohttp
import nonebot
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager

from Shadiao import waifu_finder, ark_nights, shadiao, pcr_news
from awesome.adminControl import permission as perm
from awesome.plugins.util.helper_util import get_downloaded_image_path, ark_helper
from config import SUPER_USER
from qq_bot_core import admin_control
from qq_bot_core import user_control_module, sanity_meter

pcr_api = pcr_news.GetPCRNews()
arknights_api = ark_nights.ArkHeadhunt(times=10)
ark_pool_pity = ark_nights.ArknightsPity()

get_privilege = lambda x, y: user_control_module.get_user_privilege(x, y)
timeout = aiohttp.ClientTimeout(total=5)


@nonebot.on_command('吹我', only_to_me=False)
async def do_joke_flatter(session: nonebot.CommandSession):
    flatter_api = shadiao.flatter()
    ctx = session.ctx.copy()
    user_id = ctx['user_id']
    await session.send(flatter_api.get_flatter_result(user_id))

@nonebot.on_command('清空语录', only_to_me=False)
async def clear_group_quotes(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.OWNER):
        await session.finish()

    group_id = session.get('group_id', prompt='群号？')
    if admin_control.clear_group_quote(group_id):
        await session.finish('Done!')

    await session.finish('啊这……群号不对啊……')

@nonebot.on_command('你群语录', aliases=('你组语录', '语录'), only_to_me=False)
async def get_group_quotes(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if 'group_id' not in ctx:
        await session.finish()

    await session.finish(admin_control.get_group_quote(ctx['group_id']))


@nonebot.on_command('添加语录', only_to_me=False)
async def add_group_quotes(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if 'group_id' not in ctx:
        await session.finish()

    key_word = re.sub(r'.*?添加语录[\s\r\n]*', '', ctx['raw_message']).strip()
    if '屑bot' in key_word.lower():
        await session.finish('爬')

    bot = nonebot.get_bot()
    has_image = re.findall(r'.*?\[CQ:image,file=(.*?\.image)]', key_word)
    if has_image:
        response = await bot.get_image(file=has_image[0])
        key_word = get_downloaded_image_path(response, f'{os.getcwd()}/data/lol')

        if key_word:
            admin_control.add_quote(ctx['group_id'], key_word)
            await session.finish(f'已添加！（当前总语录条数：{admin_control.get_group_quote_count(ctx["group_id"])})')
    else:
        await session.finish('啊这……')

@nonebot.on_command('说', only_to_me=False)
async def send_voice_message(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    msg: str = ctx['raw_message']
    args = msg.split()
    if len(args) < 2:
        return
    else:
        message = ''.join(args[1:])

    text = re.sub('\[CQ:.*?\]', '', message)
    text = re.sub('祈.*?雨', f'{ctx["sender"]["nickname"]}', text)
    await session.send(f'[CQ:tts,text={text}]')

@nonebot.message_preprocessor
async def message_preprocessing(_: nonebot.NoneBot, event: aiocqhttp.event, __: PluginManager):
    group_id = event.group_id
    user_id = event.user_id

    if group_id is not None:
        if not admin_control.get_data(group_id, 'enabled') \
                and not get_privilege(event['user_id'], perm.OWNER):
            raise CanceledException('Group disabled')

    if user_id is not None:
        if get_privilege(user_id, perm.BANNED) and str(user_id) != str(SUPER_USER):
            raise CanceledException('User disabled')


@nonebot.on_command('来个老婆', aliases=('来张waifu', '来个waifu', '老婆来一个'), only_to_me=False)
async def send_waifu(session: nonebot.CommandSession):
    waifu_api = waifu_finder.waifuFinder()
    path, message = waifu_api.getImage()
    if not path:
        await session.send(message)
    else:
        nonebot.logger.info(f'Get waifu pic: {path}')
        await session.send(f'[CQ:image,file=file:///{path}]\n{message}')


@nonebot.on_command('shadiao', aliases=('沙雕图', '来一张沙雕图', '机器人来张沙雕图'), only_to_me=False)
async def shadiao_send(session: nonebot.CommandSession):
    shadiao_api = shadiao.ShadiaoAPI()
    await shadiao_api.get_image_list()
    file = await shadiao_api.get_picture()
    await session.send(f'[CQ:image,file=file:///{file}]')


@nonebot.on_command('你群有多色', only_to_me=False)
async def get_setu_stat(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if 'group_id' not in ctx:
        await session.finish('本功能是群组功能')

    times, rank, yanche, delta, ark_stat, ark_pull = sanity_meter.get_usage(ctx['group_id'])
    setu_notice = f'自统计功能实装以来，你组查了{times}次色图！' \
                  f'{"位居色图查询排行榜的第" + str(rank) + "！" if rank != -1 else ""}\n' \
                  f'距离第{2 if rank == 1 else rank - 1}位相差{delta}次搜索！\n'

    yanche_notice = ('并且验车了' + str(yanche) + "次！\n") if yanche > 0 else ''
    ark_data = ''
    if ark_stat:
        ark_data += f'十连充卡共{ark_pull}次，理论消耗合成玉{ark_pull * 6000}。抽到了：\n' \
                    f"3星{ark_stat['3']}个，4星{ark_stat['4']}个，5星{ark_stat['5']}个，6星{ark_stat['6']}个"

    await session.send(setu_notice + yanche_notice + ark_data)


@nonebot.on_command('happy', aliases={'快乐时光'}, only_to_me=False)
async def start_happy_hours(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    id_num = str(ctx['user_id'])
    if get_privilege(id_num, perm.OWNER):
        if sanity_meter.happy_hours:
            sanity_meter.happy_hours = False
            await session.finish('已设置关闭快乐时光')

        sanity_meter.happy_hours = not sanity_meter.happy_hours
        await session.finish('已设置打开快乐时光')

    else:
        await session.finish('您无权使用本指令')


@nonebot.on_command('设置R18', only_to_me=False)
async def set_r18(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.WHITELIST):
        await session.finish('您无权进行该操作')

    if 'group_id' in ctx:
        id_num = ctx['group_id']
    else:
        await session.finish('请在需要禁用或开启R18的群内使用本指令')
        id_num = -1

    setting = session.get('stats', prompt='请设置开启或关闭')
    if '开' in setting:
        admin_control.set_data(id_num, 'R18', True)
        resp = '开启'
    else:
        admin_control.set_data(id_num, 'R18', False)
        resp = '关闭'

    await session.finish('Done! 已设置%s' % resp)


@nonebot.on_command('掉落查询', only_to_me=False)
async def check_pcr_drop(session: nonebot.CommandSession):
    query = session.get('group_id', prompt='请输入要查询的道具名称')
    response = await pcr_api.pcr_check(query=query)
    await session.finish(response)


@nonebot.on_command('方舟十连', only_to_me=False)
async def ten_polls(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if 'group_id' not in ctx:
        await session.send('这是群组功能')
        return

    if get_privilege(ctx['user_id'], perm.OWNER):
        arknights_api.get_randomized_results(98)

    else:
        offset = ark_pool_pity.get_offset_setting(ctx['group_id'])
        arknights_api.get_randomized_results(offset)
        class_list = arknights_api.random_class
        six_star_count = class_list.count(6)
        if 6 in class_list:
            ark_pool_pity.reset_offset(ctx['group_id'])

        five_star_count = class_list.count(5)

        data = {
            "6": six_star_count,
            "5": five_star_count,
            "4": class_list.count(4),
            "3": class_list.count(3)
        }

        if six_star_count == 0 and five_star_count == 0:
            sanity_meter.set_user_data(ctx['user_id'], 'only_four_three')

        sanity_meter.set_usage(group_id=ctx['group_id'], tag='pulls', data=data)
        sanity_meter.set_usage(group_id=ctx['group_id'], tag='pull')
        sanity_meter.set_user_data(ctx['user_id'], 'six_star_pull', six_star_count)

    qq_num = ctx['user_id']
    await session.send(
        f'[CQ:at,qq={qq_num}]\n{arknights_api.__str__()}'
    )


@nonebot.on_command('方舟up', aliases='方舟UP', only_to_me=False)
async def up_ten_polls(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.OWNER):
        await session.finish('您无权使用本功能')

    key_word: str = session.get(
        'key_word',
        prompt='使用方法：！方舟up 干员名 星级（数字）'
    )

    args = key_word.split()
    validation = ark_helper(args)
    if validation:
        await session.finish(validation)

    await session.finish(arknights_api.set_up(args[0], args[1]))

@nonebot.on_command('帮我做选择', only_to_me=False)
async def do_mcq(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    raw_message: str = ctx['raw_message']

    question_count = 1
    if len(raw_message.split()) == 2:
        try:
            question_count = int(raw_message.split()[1])
        except TypeError:
            question_count = 1

    answer = '选'
    for i in range(question_count):
        answer += f'{chr(random.randint(65, 68))}'

    await session.send(answer + '。')

@nonebot.on_command('方舟up重置', aliases='方舟UP重置', only_to_me=False)
async def reset_ark_up(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.OWNER):
        await session.finish('您无权使用本功能')

    arknights_api.clear_ups()
    await session.finish('Done!')


@nonebot.on_command('添加干员', aliases='', only_to_me=False)
async def add_ark_op(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.OWNER):
        await session.finish('您无权使用本功能')

    key_word: str = session.get(
        'key_word',
        prompt='使用方法：！方舟up 干员名 星级（数字）'
    )

    args = key_word.split()
    validation = ark_helper(args)
    if validation:
        await session.finish(validation)

    await session.finish(arknights_api.add_op(args[0], args[1]))


@nonebot.on_command('统计', only_to_me=False)
async def stat_player(session: nonebot.CommandSession):
    get_stat = lambda key, lis: lis[key] if key in lis else 0
    ctx = session.ctx.copy()
    user_id = ctx['user_id']
    statDict = sanity_meter.get_user_data(user_id)
    if not statDict:
        await session.send(f'[CQ:at,qq={user_id}]还没有数据哦~')
    else:
        poker_win = get_stat('poker', statDict)
        six_star_pull = get_stat('six_star_pull', statDict)
        yanche = get_stat('yanche', statDict)
        setu_stat = get_stat('setu', statDict)
        question = get_stat('question', statDict)
        unlucky = get_stat('only_four_three', statDict)
        same = get_stat('hit_xp', statDict)
        zc = get_stat('zc', statDict)
        chp = get_stat('chp', statDict)
        roulette = get_stat('roulette', statDict)
        horse_race = get_stat('horse_race', statDict)

        await session.send(f'用户[CQ:at,qq={user_id}]：\n' +
                           (f'比大小赢得{poker_win}次\n' if poker_win != 0 else '') +
                           (f'方舟抽卡共抽到{six_star_pull}个六星干员\n' if six_star_pull != 0 else '') +
                           (f'紫气东来{unlucky}次\n' if unlucky != 0 else '') +
                           (f'验车{yanche}次\n' if yanche != 0 else '') +
                           (f'查了{setu_stat}次的色图！\n' if setu_stat != 0 else '') +
                           (f'问了{question}次问题\n' if question != 0 else '') +
                           (f'和bot主人 臭 味 相 投{same}次\n' if same != 0 else '') +
                           (f'嘴臭{zc}次\n' if zc != 0 else '') +
                           (f'彩虹屁{chp}次\n' if chp != 0 else '') +
                           (f'轮盘赌被处死{roulette}次\n' if roulette != 0 else '') +
                           (f'赛马获胜{horse_race}次\n' if horse_race != 0 else '')

                           )


@nonebot.on_command('统计xp', only_to_me=False)
async def get_xp_stat_data(session: nonebot.CommandSession):
    xp_stat = sanity_meter.get_xp_data()
    response = ''
    for item, keys in xp_stat.items():
        response += f'关键词：{item} --> Hit: {keys}\n'

    await session.finish(response)


@nonebot.on_command('娱乐开关', only_to_me=False)
async def entertain_switch(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    id_num = str(ctx['user_id'])
    if not get_privilege(id_num, perm.WHITELIST):
        await session.finish('您无权进行该操作')

    group_id = session.get('group_id', prompt='请输入要禁用所有功能的qq群')
    if not str(group_id).isdigit():
        await session.finish('这不是qq号哦~')

    if admin_control.get_data(group_id, 'enabled'):
        admin_control.set_data(group_id, 'enabled', False)
        await session.finish('已禁用娱乐功能！')
    else:
        admin_control.set_data(group_id, 'enabled', True)
        await session.finish('已开启娱乐功能！')


@check_pcr_drop.args_parser
@entertain_switch.args_parser
@clear_group_quotes.args_parser
async def _set_group_property(session: nonebot.CommandSession):
    stripped_arg = session.current_arg_text
    if session.is_first_run:
        if stripped_arg:
            session.state['group_id'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('qq组号不能为空')

    session.state[session.current_key] = stripped_arg


@nonebot.on_command('闪照设置', only_to_me=False)
async def set_exempt(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if not get_privilege(ctx['user_id'], perm.ADMIN) or 'group_id' not in ctx:
        return

    group_id = ctx['group_id']
    if admin_control.get_data(group_id, 'exempt'):
        admin_control.set_data(group_id, 'exempt', False)
        await session.finish('已打开R18闪照发送模式')

    else:
        admin_control.set_data(group_id, 'exempt', True)
        await session.finish('本群R18图将不再已闪照形式发布')


@nonebot.on_command('验车', only_to_me=False)
async def av_validator(session: nonebot.CommandSession):
    ctx = session.ctx.copy()
    if get_privilege(ctx['user_id'], perm.BANNED):
        await session.finish('略略略，我主人把你拉黑了。哈↑哈↑哈')

    if not admin_control.get_data(ctx['group_id'], 'R18'):
        await session.finish('请联系BOT管理员开启本群R18权限')

    key_word = session.get('key_word', prompt='在？你要让我查什么啊baka')
    validator = shadiao.Avalidator(text=key_word)
    await validator.get_page_text()
    if 'group_id' in ctx:
        sanity_meter.set_usage(ctx['group_id'], tag='yanche')
        sanity_meter.set_user_data(ctx['user_id'], 'yanche')

    await session.finish(await validator.get_content())



@add_ark_op.args_parser
@up_ten_polls.args_parser
@av_validator.args_parser
async def _(session: nonebot.CommandSession):
    stripped_arg = session.current_arg_text
    if session.is_first_run:
        if stripped_arg:
            session.state['key_word'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('要查询的关键词不能为空')

    session.state[session.current_key] = stripped_arg


@nonebot.on_command('嘴臭一个', aliases=('骂我', '你再骂', '小嘴抹蜜', '嘴臭一下', '机器人骂我'), only_to_me=False)
async def zuiChou(session: nonebot.CommandSession):
    ctx = session.ctx.copy()

    if get_privilege(ctx['user_id'], perm.BANNED):
        await session.finish('略略略，我主人把你拉黑了。哈↑哈↑哈')

    if 'group_id' in ctx:
        sanity_meter.set_user_data(ctx['user_id'], 'zc')

    random.seed(time.time_ns())
    rand_num = random.randint(0, 100)
    if rand_num > 25:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as client:
                async with client.get(
                        'https://nmsl.shadiao.app/api.php?level=min&from=qiyu'
                ) as page:
                    text = await page.text()

        except Exception as err:
            await session.send('骂不出来了！')
            nonebot.logger.warning(f'Request to nmsl API failed. {err}')
            return

    elif rand_num > 10:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as client:
                async with client.get(
                        'https://nmsl.shadiao.app/api.php?level=max&from=qiyu'
                ) as page:
                    text = await page.text()

        except Exception as err:
            await session.send('骂不出来了！')
            nonebot.logger.warning(f'Request to nmsl API failed. {err}')
            return

    else:
        file = os.listdir('data/dl/zuichou')
        file = random.choice(file)
        text = f"[CQ:image,file=file:///{os.getcwd()}/data/dl/zuichou/{file}]"

    msg = str(ctx['raw_message'])

    if re.match(r'.*?\[CQ:at,qq=.*?\]', msg):
        qq = re.findall(r'\[CQ:at,qq=(.*?)\]', msg)[0]
        if qq != "all":
            if not get_privilege(qq, perm.ADMIN):
                await session.finish(f"[CQ:at,qq={int(qq)}] {text}")
            else:
                await session.finish(f"[CQ:at,qq={ctx['user_id']}] {text}")

    await session.send(text)


@nonebot.on_command('彩虹屁', aliases=('拍个马屁', '拍马屁', '舔TA'), only_to_me=False)
async def cai_hong_pi(session: nonebot.CommandSession):
    ctx = session.ctx.copy()

    if get_privilege(ctx['user_id'], perm.BANNED):
        await session.finish('略略略，我主人把你拉黑了。哈↑哈↑哈')

    if 'group_id' in ctx:
        sanity_meter.set_user_data(ctx['user_id'], 'chp')

    try:
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.get(
                    'https://chp.shadiao.app/api.php?from=qiyu'
            ) as req:
                text = await req.text()

    except Exception as err:
        await session.send('拍马蹄上了_(:зゝ∠)_')
        nonebot.logger.warning(f'Reqeust to chp API failed, {err}')
        return

    msg = str(ctx['raw_message'])

    do_tts = '语音' in msg

    if re.match(r'.*?\[CQ:at,qq=.*?\]', msg):
        qq = re.findall(r'\[CQ:at,qq=(.*?)\]', msg)[0]
        if qq != "all":
            if not do_tts:
                await session.send(f"[CQ:at,qq={int(qq)}] {text}")
                return

    await session.send(f'[CQ:tts,text={text}]' if do_tts else f'[CQ:reply,id={ctx["message_id"]}]/{text}')
