<template>
  <div class="dropdown">
    <div tabindex="0" class="click">
      <slot name="button">
        <i class="fa-solid fa-ellipsis-vertical"></i>
      </slot>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-1 w-52 p-2 shadow-sm">
      <slot>

      </slot>
    </ul>
  </div>
</template>