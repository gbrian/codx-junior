<template>
    <div class="click text-xs flex gap-1 items-center tooltip border rounded-xl px-1 border-slate-400/30"
        :data-tip="`Go to ${project.project_name}`">
        <div class="max-w-16 overflow-hidden text-nowrap text-ellipsis">
            {{ project.project_name }}
        </div>
    </div>
</template>
<script>
export default {
    props: ['project']
}
</script>