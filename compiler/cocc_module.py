#coding=utf8

import cocc_token

need_update_git = False
std_lib_dir = None
usr_lib_dir = None

class ModuleName:
    class InvalidModuleName(Exception):
        pass

    def __init__(self, mn_str):
        def fail():
            raise ModuleName.InvalidModuleName()

        if mn_str.startswith('"'):
            if mn_str.count('"') != 2:
                fail()
            git_repo, mn = mn_str[1 :].split('"')
            if not mn.startswith("/"):
                fail()
            mnpl = mn[1 :].split("/")
        else:
            pl = mn_str.split("/")
            if not pl:
                fail()
            if "." in pl[0]:
                if len(pl) <= 3:
                    fail()
                git_repo = "/".join(pl[: 3])
                mnpl = pl[3 :]
            else:
                git_repo = None
                mnpl = pl

        if git_repo is not None:
            for q in '"', "'", "`":
                if q in git_repo:
                    fail()
            git_repo_parts = git_repo.split("/")
            if not (len(git_repo_parts) == 3 and all(git_repo_parts) and "." in git_repo_parts[0]):
                fail()

        if not (mnpl and all([cocc_token.is_valid_name(mnp) for mnp in mnpl])):
            fail()

        self.git_repo = git_repo
        self.mnpl = mnpl

    __str__ = __repr__ = (
        lambda self: "%s%s" % ("" if self.git_repo is None else '"%s"/' % self.git_repo, "/".join(self.mnpl)))
