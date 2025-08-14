<script setup>
</script>
<template>
  <div class="p-2 w-full h-full flex flex-col gap-2">
    <div class="text-2xl">File finder</div>
    <vue-finder class="grow" :request="request" path="/"></vue-finder>
  </div>
</template>
<script>
export default {
  computed: {
    request() {
      const { codx_path } = this.$project
      const { headers } = this.$storex.api.connection
      return {
        baseUrl: "/api/file-finder",
        // Additional headers & params & body
        headers,
        params: { codx_path },
        body: { },
        // XSRF Token header name
        xsrfHeaderName: "X-CSRF-TOKEN",
        transformRequest: req => {
          console.log("file finder req", req, arguments)
          return req
        },
        fetchResponseInterceptor: async res => {
          const body = await res.clone().json()
          console.log("file finder res", res, body)
          body.files.map(file => ({
            ...file,
            url: `/api/files?codx_path=${codx_path}&path=${file.path}`
          }))
          return new Response(JSON.stringify(body), {
            status: res.status,
            statusText: res.statusText,
            headers: Object.fromEntries(res.headers.entries())
          });
        }
      }
    }
  }
}
</script>
<style>
.vuefinder__main__relative.vuefinder__main__container {
  background-color: transparent !important;
  max-height: none !important;
  height: 100% !important;
}
</style>