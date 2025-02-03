<template>
    <div class="rounded-lg px-1 click hover:underline text-xs flex gap-1 items-center tooltip"
        :data-tip="`Go to ${project.project_name}`">
        <img class="w-4 rounded-full bg-base-300" :src="project.project_icon"/>
        <div class="max-w-12 overflow-hidden text-nowrap text-ellipsis">
            {{ project.project_name }}
        </div>
    </div>
</template>
<script>
export default {
    props: ['project']
}
</script>