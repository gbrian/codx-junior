<template>
    <div :class="['h-16 sm:w-full shrink-0 flex flex-col gap-1 items-center items-center hover:bg-base-300 hover:shadow opacity-80 hover:opacity-100 rounded-md click']">
        <a class="h-6 w-6 mt-4 tooltip z-50" :class="right ? 'tooltip-top' : 'tooltip-right'" :data-tip="project?.project_name">
            <div class="avatar">
                <div class="w-6 rounded-full">
                    <img :src="project?.project_icon || '/only_icon.png'" />
                </div>
            </div>
        </a>
        <div class="text-xs w-16 text-center overflow-hidden text-nowrap px-1 font-bold">
            {{ project?.project_name }}
        </div>
    </div>
</template>
<script>
export default {
    props: ['project', 'right']
}
</script>