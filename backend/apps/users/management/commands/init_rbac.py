"""
init_rbac - 初始化 RBAC 权限体系
执行: python manage.py init_rbac
"""
from django.core.management.base import BaseCommand
from apps.users.models import User, Role, MenuPermission


class Command(BaseCommand):
    help = '初始化 RBAC 权限体系 - 创建默认角色、菜单、超级管理员'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='清空后重建所有权限数据')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== 开始初始化 RBAC 权限体系 ==='))

        # 1. 默认角色
        roles_data = [
            {
                'code': 'admin',
                'name': '超级管理员',
                'description': '拥有系统所有权限',
                'is_builtin': True,
                'sort_order': 1,
            },
            {
                'code': 'developer',
                'name': '开发人员',
                'description': '负责开发和维护测试用例',
                'is_builtin': True,
                'sort_order': 2,
            },
            {
                'code': 'tester',
                'name': '测试人员',
                'description': '执行测试用例，上报缺陷',
                'is_builtin': True,
                'sort_order': 3,
            },
        ]

        roles = {}
        for r in roles_data:
            role, created = Role.objects.update_or_create(
                code=r['code'],
                defaults=r
            )
            roles[r['code']] = role
            self.stdout.write(f'  角色: {role.name} ({role.code}) - {"创建" if created else "已存在"}')

        # 2. 菜单 & 权限树
        menus_data = [
            # ============ 顶层目录 ============
            {
                'name': '首页',
                'menu_type': 'directory',
                'path': '/',
                'icon': 'HomeFilled',
                'component': None,
                'children': [
                    {
                        'name': '工作台',
                        'menu_type': 'menu',
                        'path': 'dashboard',
                        'icon': 'DataBoard',
                        'component': 'views/dashboard/index',
                        'permission_code': 'dashboard:view',
                    },
                ]
            },
            {
                'name': '系统管理',
                'menu_type': 'directory',
                'path': '/system',
                'icon': 'Setting',
                'component': None,
                'children': [
                    {
                        'name': '用户管理',
                        'menu_type': 'menu',
                        'path': 'user',
                        'icon': 'User',
                        'component': 'views/system/user/index',
                        'permission_code': 'system:user:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'system:user:detail'},
                            {'name': '新增', 'permission_code': 'system:user:create'},
                            {'name': '编辑', 'permission_code': 'system:user:update'},
                            {'name': '删除', 'permission_code': 'system:user:delete'},
                            {'name': '重置密码', 'permission_code': 'system:user:reset_password'},
                        ]
                    },
                    {
                        'name': '角色权限',
                        'menu_type': 'menu',
                        'path': 'role',
                        'icon': 'Lock',
                        'component': 'views/system/role/index',
                        'permission_code': 'system:role:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'system:role:detail'},
                            {'name': '新增', 'permission_code': 'system:role:create'},
                            {'name': '编辑', 'permission_code': 'system:role:update'},
                            {'name': '删除', 'permission_code': 'system:role:delete'},
                        ]
                    },
                    {
                        'name': '菜单管理',
                        'menu_type': 'menu',
                        'path': 'menu',
                        'icon': 'Menu',
                        'component': 'views/system/menu/index',
                        'permission_code': 'system:menu:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'system:menu:detail'},
                            {'name': '新增', 'permission_code': 'system:menu:create'},
                            {'name': '编辑', 'permission_code': 'system:menu:update'},
                            {'name': '删除', 'permission_code': 'system:menu:delete'},
                        ]
                    },
                ]
            },
            {
                'name': '项目管理',
                'menu_type': 'directory',
                'path': '/project',
                'icon': 'Folder',
                'component': None,
                'children': [
                    {
                        'name': '项目列表',
                        'menu_type': 'menu',
                        'path': 'list',
                        'icon': 'Files',
                        'component': 'views/project/list/index',
                        'permission_code': 'project:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'project:detail'},
                            {'name': '新增', 'permission_code': 'project:create'},
                            {'name': '编辑', 'permission_code': 'project:update'},
                            {'name': '删除', 'permission_code': 'project:delete'},
                        ]
                    },
                    {
                        'name': '测试模块',
                        'menu_type': 'menu',
                        'path': 'module',
                        'icon': 'Grid',
                        'component': 'views/project/module/index',
                        'permission_code': 'project:module:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'project:module:detail'},
                            {'name': '新增', 'permission_code': 'project:module:create'},
                            {'name': '编辑', 'permission_code': 'project:module:update'},
                            {'name': '删除', 'permission_code': 'project:module:delete'},
                        ]
                    },
                ]
            },
            {
                'name': '测试用例',
                'menu_type': 'directory',
                'path': '/testcase',
                'icon': 'Document',
                'component': None,
                'children': [
                    {
                        'name': '用例列表',
                        'menu_type': 'menu',
                        'path': 'list',
                        'icon': 'List',
                        'component': 'views/testcase/list/index',
                        'permission_code': 'testcase:view',
                        'buttons': [
                            {'name': '查看', 'permission_code': 'testcase:detail'},
                            {'name': '新增', 'permission_code': 'testcase:create'},
                            {'name': '编辑', 'permission_code': 'testcase:edit'},
                            {'name': '删除', 'permission_code': 'testcase:delete'},
                            {'name': '导入导出', 'permission_code': 'testcase:import_export'},
                        ]
                    },
                    {
                        'name': 'AI 生成用例',
                        'menu_type': 'menu',
                        'path': 'ai-generate',
                        'icon': 'MagicStick',
                        'component': 'views/testcase/ai-generate/index',
                        'permission_code': 'testcase:ai_generate',
                    },
                ]
            },
            {
                'name': '缺陷管理',
                'menu_type': 'directory',
                'path': '/bug',
                'icon': 'Warning',
                'component': None,
                'children': [
                    {
                        'name': 'Bug 列表',
                        'menu_type': 'menu',
                        'path': 'list',
                        'icon': 'Warning',
                        'component': 'views/bug/list/index',
                        'permission_code': 'bug:view',
                        'buttons': [
                            {'name': '新增', 'permission_code': 'bug:create'},
                            {'name': '编辑', 'permission_code': 'bug:edit'},
                            {'name': '删除', 'permission_code': 'bug:delete'},
                            {'name': '状态流转', 'permission_code': 'bug:transition'},
                        ]
                    },
                ]
            },
            {
                'name': '测试执行',
                'menu_type': 'directory',
                'path': '/execution',
                'icon': 'VideoPlay',
                'component': None,
                'children': [
                    {
                        'name': '执行计划',
                        'menu_type': 'menu',
                        'path': 'plan',
                        'icon': 'Clock',
                        'component': 'views/execution/plan/index',
                        'permission_code': 'execution:plan:view',
                    },
                    {
                        'name': '执行记录',
                        'menu_type': 'menu',
                        'path': 'record',
                        'icon': 'Tickets',
                        'component': 'views/execution/record/index',
                        'permission_code': 'execution:record:view',
                    },
                ]
            },
        ]

        # 构建菜单树 (幂等 update_or_create)
        all_perm_objects = []

        def create_menu(parent, data, sort_base=0):
            """递归创建菜单树"""
            menu, _ = MenuPermission.objects.update_or_create(
                name=data['name'],
                parent=parent,
                defaults={
                    'menu_type': data['menu_type'],
                    'path': data.get('path', ''),
                    'icon': data.get('icon', ''),
                    'component': data.get('component', ''),
                    'permission_code': data.get('permission_code', ''),
                    'sort_order': sort_base,
                }
            )
            all_perm_objects.append(menu)

            # 按钮
            for i, btn in enumerate(data.get('buttons', [])):
                btn_obj, _ = MenuPermission.objects.update_or_create(
                    name=btn['name'],
                    parent=menu,
                    defaults={
                        'menu_type': 'button',
                        'permission_code': btn.get('permission_code', ''),
                        'sort_order': i,
                    }
                )
                all_perm_objects.append(btn_obj)

            # 子菜单
            for i, child in enumerate(data.get('children', [])):
                create_menu(menu, child, i + 1)

        for i, top in enumerate(menus_data):
            create_menu(None, top, i + 1)

        self.stdout.write(f'  菜单/权限: 共 {len(all_perm_objects)} 个节点')

        # 3. 分配权限给角色
        admin_role = roles['admin']
        admin_role.permissions.set(all_perm_objects)
        self.stdout.write(f'  角色 [{admin_role.name}] 已分配全部 {len(all_perm_objects)} 个权限')

        # developer: 除系统管理(用户/角色/菜单)外全部权限
        system_menu = MenuPermission.objects.filter(name='系统管理', menu_type='directory').first()
        system_perm_ids = set()
        if system_menu:
            system_perm_ids = set(MenuPermission.objects.filter(
                pk__in=[system_menu.pk],
                children__pk__isnull=False,
            ).values_list('pk', flat=True))
            # 加上所有子节点
            all_system = MenuPermission.objects.filter(
                parent__in=[system_menu.pk] + list(
                    MenuPermission.objects.filter(parent=system_menu).values_list('pk', flat=True)
                )
            ).values_list('pk', flat=True)
            system_perm_ids = set([system_menu.pk] + list(all_system))

        dev_perms = [p for p in all_perm_objects if p.pk not in system_perm_ids]
        roles['developer'].permissions.set(dev_perms)
        self.stdout.write(f'  角色 [{roles["developer"].name}] 已分配 {len(dev_perms)} 个权限')

        # tester: 非系统管理模块的菜单可见 + 仅查看类按钮权限
        # 例外: 测试用例模块开放全部权限; 缺陷可上报/编辑/流转, 不可删除
        tester_bug_codes = {'bug:view', 'bug:create', 'bug:edit', 'bug:transition'}
        tester_perms = [
            p for p in all_perm_objects
            if p.pk not in system_perm_ids
            and (
                (p.permission_code or '').startswith('testcase:')
                or (p.permission_code or '') in tester_bug_codes
                or p.menu_type != 'button'
                or (p.permission_code or '').endswith((':view', ':detail'))
            )
        ]
        roles['tester'].permissions.set(tester_perms)
        self.stdout.write(f'  角色 [{roles["tester"].name}] 已分配 {len(tester_perms)} 个权限')

        # 4. 默认超级管理员
        admin_user, created = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': 'admin@testauto.local',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            }
        )
        if created or not admin_user.check_password('admin123456'):
            admin_user.set_password('admin123456')
            admin_user.save()
        admin_user.roles.set([admin_role])
        self.stdout.write(f'  超级管理员: admin / admin123456 - {"创建" if created else "已存在"}')

        self.stdout.write(self.style.SUCCESS('=== RBAC 初始化完成 ==='))
