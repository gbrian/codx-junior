<script setup>
import { RemoteDriver } from 'vuefinder';

</script>
<template>
  <div class="w-full h-full flex flex-col gap-2 p-1 md:p-2">
    <div class="text-2xl">File finder</div>
    <vue-finder id="my_vuefinder" class="grow" 
    :driver="driver"
    :config="{
      initialPath: 'local://',
      persist: true,
    }"
    ></vue-finder>
  </div>
</template>
<script>
export default {
  computed: {
    driver() {
      const { codx_path } = this.$project
      const { headers } = this.$storex.api.connection
      const vueFinderHeaders = {
        ...headers,
        "x-codx-path": codx_path
      }
      return new RemoteDriver({
        baseURL: '/api/file-finder',
        url: {
          list: '/files',
          upload: '/upload',
          delete: '/delete',
          rename: '/rename',
          archive: '/archive',
          unarchive: '/unarchive',
          createFile: '/create-file',
          createFolder: '/create-folder',
          search: '/search',
          preview: '/preview',
          copy: '/copy',
          move: '/move',
          save: '/save',
          download: '/download',
        },
        // Additional headers & params & body
        headers: vueFinderHeaders,
        params: { codx_path },
        body: { },
        // XSRF Token header name
        xsrfHeaderName: "X-CSRF-TOKEN",
        transformRequest: req => {
          console.log("file finder req", req, arguments)
          return req
        },
        fetchResponseInterceptor: async res => {
          if (res.headers.get("content-type") !== 'application/json') {
            return res
          }
          
          const body = await res.clone().json()
          console.log("file finder res", res, body)
          body.files?.map(file => ({
            ...file,
            url: `/api/files?codx_path=${codx_path}&path=${file.path}`
          }))
          return new Response(JSON.stringify(body), {
            status: res.status,
            statusText: res.statusText,
            headers: Object.fromEntries(res.headers.entries())
          });
        }
      });
    },
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
          if (res.headers.get("content-type") !== 'application/json') {
            return res
          }
          
          const body = await res.clone().json()
          console.log("file finder res", res, body)
          body.files?.map(file => ({
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
.vuefinder > div {
  height: 100%;
}
.vuefinder__main__relative.vuefinder__main__container {
  background-color: transparent !important;
  max-height: none !important;
  height: 100% !important;
}
</style>