<template>
    <div :class="['h-16 sm:w-full shrink-0 flex flex-col gap-1 items-center items-center hover:bg-base-100 click',
        tabIx == 'home' && 'bg-base-100'
    ]">
        <a class="h-6 w-6 mt-4 tooltip tooltip-right" data-tip="Projects">
            <div class="avatar">
                <div class="w-6 rounded-full">
                    <img :src="$project.activeProject?.project_icon || '/only_icon.png'" />
                </div>
            </div>
        </a>
        <div class="text-xs w-16 text-center overflow-hidden text-nowrap px-1 font-bold">
            {{ $project.activeProject?.project_name }}
        </div>
    </div>
</template>
<script>
export default {
    props: ['tabIx']
}
</script>