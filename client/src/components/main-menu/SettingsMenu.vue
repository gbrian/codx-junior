<script setup>
import MenubarSub from './MenubarSub.vue'
import MenubarItem from './MenubarItem.vue'
</script>
<template>
    <MenubarSub title="Settings">
        <template v-slot:menubaritem>
            <i class="fa-solid fa-gear"></i>
            Settings
        </template>
        <div class="font-bold px-2 hover:bg-base-300">
            Settings
        </div>
        <MenubarItem @click="$ui.setActiveTab('account')">
            User account
        </MenubarItem>

        <MenubarItem @click="$ui.setActiveTab('settings')" v-if="$users.isProjectAdmin">
            Project settings
        </MenubarItem>


        <MenubarItem v-if="$project && $storex.api.permissions.isProjectAdmin">
            <a class="flex gap-1 tooltip tooltip-right click" data-tip="Knowledge settings"
                @click.stop="$ui.setActiveTab('knowledge_settings')">
                Knowledge settings
            </a>
        </MenubarItem>

        <MenubarItem class="flex gap-2 hover:bg-base-300" @click="$ui.setActiveTab('global-settings')"
            v-if="$users.isAdmin">
            Global settings
        </MenubarItem>

        <MenubarSub title="Miscellaneous">
            <div class="font-bold px-2 hover:bg-base-300">
                Miscellaneous
            </div>

            <MenubarItem v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1 tooltip tooltip-right click" data-tip="Logs" @click="$ui.toggleLogs()">
                    View logs
                </a>
            </MenubarItem>
            <MenubarItem v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1 tooltip tooltip-right click" data-tip="Logs" @click="$ui.openChatLogs()">
                    Chat logs
                </a>
            </MenubarItem>
            <MenubarItem class="flex gap-2 hover:bg-base-300" v-if="$ui.isMobile" @click="showEruda">
                Mobile console
            </MenubarItem>
        </MenubarSub>

        <MenubarItem>
            <div class="flex items-center justify-between w-full" @click.stop="">
                <span class="flex items-center gap-2 select-none">
                    Advanced mode
                </span>
                <input 
                    type="checkbox" 
                    class="toggle toggle-sm toggle-primary" 
                    :checked="$storex.ui.viewMode !== 'vibe'"
                    @change="toggleViewMode"
                />
            </div>
        </MenubarItem>

        <MenubarItem>
            <a class="flex gap-4 items-center gap-2 tooltip select select-sm" data-tip="Voice language">
                <i class="fa-solid fa-microphone-lines"></i>
                <select class="select select-sm" @change="$ui.setVoiceLanguage($event.target.value)" @click.stop="">
                    <option v-for="key, lang in $ui.voiceLanguages" :key="lang" :selected="$ui.voiceLanguage === lang"
                        :value="lang">
                        {{ key }}
                    </option>
                </select>
            </a>
        </MenubarItem>
    </MenubarSub>
</template>
<script>
export default {
    computed: {
        workspaces() {
            return this.$storex.projects.projectApps.reduce((acc, app) => {
                const apps = acc[app.workspaceName] || []
                apps.push(app)
                return {
                    ...acc,
                    [app.workspaceName]: apps
                }
            }, {})
        }
    },
    methods: {
        toggleViewMode() {
            if (this.$storex.ui.viewMode === 'vibe') {
                this.$storex.ui.setExpertMode()
            } else {
                this.$storex.ui.setVibeMode()
            }
        },
        toggleAppPanel(app) {
            app = this.$ui.openApps[app.key] || app
            this.$ui.showApp({
                ...app,
                left: !app?.left,
                ts: new Date().getTime()
            })
        },
        showEruda() {
            window.eruda.init()
        }
    }
}
</script>