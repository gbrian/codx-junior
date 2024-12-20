# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "KDE Plasms desktop", "created_at": "2024-10-19T21:46:54.377726", "updated_at": "2024-10-20T09:10:56.553643", "mode": "chat", "board": "", "column": "Infrastructure", "column_index": 2, "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "hide": false, "improvement": false, "created_at": "2024-10-19T22:28:58.380268", "images": [], "files": []}]]
Allow login for root without a password
```ssdm

#%PAM-1.0


# Block login if they are globally disabled
auth    requisite       pam_nologin.so
auth    required        pam_succeed_if.so user != root quiet_success


# auth    sufficient      pam_succeed_if.so user ingroup nopasswdlogin
@include common-auth
# gnome_keyring breaks QProcess
-auth   optional        pam_gnome_keyring.so
-auth   optional        pam_kwallet5.so


@include common-account


# SELinux needs to be the first session rule.  This ensures that any
# lingering context has been cleared.  Without this it is possible that a
# module could execute code in the wrong domain.
session [success=ok ignore=ignore module_unknown=ignore default=bad] pam_selinux.so close
# Create a new session keyring.
session optional        pam_keyinit.so force revoke
session required        pam_limits.so
session required        pam_loginuid.so
@include common-session
# SELinux needs to intervene at login time to ensure that the process starts
# in the proper default security context.  Only sessions which are intended
# to run in the user's context should be run after this.
session [success=ok ignore=ignore module_unknown=ignore default=bad] pam_selinux.so open
-session optional       pam_gnome_keyring.so auto_start
-session optional       pam_kwallet5.so auto_start


@include common-password


# From the pam_env man page
# Since setting of PAM environment variables can have side effects to other modules, this module should be the last one on the stack.


# Load environment from /etc/environment
session required        pam_env.so


# Load environment from /etc/default/locale and ~/.pam_environment
session required        pam_env.so envfile=/etc/default/locale user_readenv=1
```