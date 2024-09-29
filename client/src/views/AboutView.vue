<template>
  <div class="text-xl">
    <h1>This is an about page</h1>
  </div>
</template>
<script>
export default {
  props: ['property1'],
  data () {
    return {
      someData: "withValue"
    }
  },
  created () {},
  mounted () {},
  computed: {
    aComputedProperty () {
      return "a"
    }
  },
  methods: {
    myMethodDoesSomething() {
    }
  }
}
</script>