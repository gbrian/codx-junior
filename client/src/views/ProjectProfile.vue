<template>
  <div class="bg-gray-900 text-white">
    <div class="container mx-auto p-4">
      <div class="flex flex-col items-center">
        <img src="http://path/to/project-icon.jpg" alt="Project Icon" class="rounded-full w-36 h-36">
        <h1 class="text-2xl font-bold mt-4">Gustavo Brian</h1>
        <p class="text-gray-400">@gbrian</p>
        <button class="btn btn-primary mt-2">Edit profile</button>
        <div class="flex mt-4">
          <span class="mr-4">28 followers</span>
          <span>15 following</span>
        </div>
        <div class="mt-4 text-center">
          <p>Palma de Mallorca, Spain</p>
          <p>gustavo.brian@gmail.com</p>
          <p><a href="https://es.linkedin.com/in/gustavo-brian-núñez-segade-a5710912" class="text-blue-500">LinkedIn</a></p>
        </div>
      </div>

      <div class="mt-8">
        <h2 class="text-xl font-bold">Achievements</h2>
        <div class="flex justify-around mt-4">
          <img src="http://path/to/achievement1.jpg" alt="Achievement 1" class="w-12 h-12">
          <img src="http://path/to/achievement2.jpg" alt="Achievement 2" class="w-12 h-12">
          <img src="http://path/to/achievement3.jpg" alt="Achievement 3" class="w-12 h-12">
        </div>
      </div>

      <div class="mt-8">
        <h2 class="text-xl font-bold">Popular repositories</h2>
        <div class="grid grid-cols-2 gap-4 mt-4">
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">grafana-simple-sql-datasource</h3>
            <p class="text-gray-400">Grafana SQL datasource</p>
            <div class="flex items-center mt-2">
              <span class="text-yellow-500">JavaScript</span>
              <span class="ml-auto">62 stars</span>
              <span class="ml-2">20 forks</span>
            </div>
          </div>
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">grafana-echart-panel</h3>
            <p class="text-gray-400">Grafana plugin panel for Echart</p>
            <div class="flex items-center mt-2">
              <span class="text-yellow-500">JavaScript</span>
              <span class="ml-auto">42 stars</span>
              <span class="ml-2">18 forks</span>
            </div>
          </div>
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">grafana-timelon-datasource</h3>
            <p class="text-gray-400">ELK Timelion's data source for Grafana</p>
            <div class="flex items-center mt-2">
              <span class="text-yellow-500">JavaScript</span>
              <span class="ml-auto">15 stars</span>
              <span class="ml-2">12 forks</span>
            </div>
          </div>
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">bibot</h3>
            <p class="text-gray-400">Business Intelligence Bot</p>
            <div class="flex items-center mt-2">
              <span class="text-yellow-500">JavaScript</span>
              <span class="ml-auto">8 stars</span>
              <span class="ml-2">5 forks</span>
            </div>
          </div>
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">grafana-hetzner-datasource</h3>
            <p class="text-gray-400">Grafana plugin datasource</p>
            <div class="flex items-center mt-2">
              <span class="text-yellow-500">JavaScript</span>
              <span class="ml-auto">6 stars</span>
              <span class="ml-2">1 fork</span>
            </div>
          </div>
          <div class="bg-gray-800 p-4 rounded">
            <h3 class="text-lg font-semibold">Travel-aipi</h3>
            <p class="text-gray-400">AI powered Travel API</p>
            <div class="flex items-center mt-2">
              <span class="text-blue-500">Python</span>
              <span class="ml-auto">2 stars</span>
              <span class="ml-2">4 forks</span>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-8">
        <h2 class="text-xl font-bold">170 contributions in the last year</h2>
        <div class="bg-gray-800 p-4 rounded mt-4">
          <!-- Contribution graph implementation -->
        </div>
      </div>

      <div class="mt-8">
        <h2 class="text-xl font-bold">Contribution activity</h2>
        <div class="bg-gray-800 p-4 rounded mt-4">
          <!-- Contribution activity implementation -->
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ProfileHeader from '@/components/board/ProfileHeader.vue';
import Achievements from '@/components/board/Achievements.vue';
import LinkedProjects from '@/components/board/LinkedProjects.vue';
import ContributionGraph from '@/components/board/ContributionGraph.vue';
import ContributionActivity from '@/components/board/ContributionActivity.vue';
import SettingsAndCustomization from '@/components/board/SettingsAndCustomization.vue';

export default {
  components: {
    ProfileHeader,
    Achievements,
    LinkedProjects,
    ContributionGraph,
    ContributionActivity,
    SettingsAndCustomization
  }
}
</script>