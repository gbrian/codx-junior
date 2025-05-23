When writing vue files always follow this best parctices:
Vue files must always follow this structure in this order.
No other elements are valid:
```example vue file
<script setup>
import Component from './component.vue'
import markdown from 'mardown'
</script>
<template>
<div class="w.full h-full flex gap-2">
</div>
</template>
<script>
export default {
props: [].
data (){
// Reactive data, don't use "ref"
 return { myVariable: null }
},
computed: {},
watch: {},
methods: {}
}
</sctipt>
```
* No need to import ref, computed or mapState 
* export default component object
* Use component "data" method to return an object variables
* Use component "computed" to define computed properties
" Use component "methods" to define component methods 
* Use "this.$storex" or "$storex" to access store data.
* To access vue store data use "$storex"
* "script setup" section contains ONLY imports, no variables, properties bnor methods
* Use TailwindCSS classes for styling, always consider mobile styles
* Vue component definition will be exporting a default object like, without ref, nor computed imports
* Don't use ";" in the javascript or typescript code
* Avoid long functions
* Add short and concise comments for complex functions
* Don't use <style> elements, use TailWindCSS classes