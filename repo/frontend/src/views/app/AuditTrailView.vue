<template>
  <section>
    <h1>Audit Trail</h1>
    <p>View operational audit events scoped to your role and store.</p>

    <section class="panel">
      <h2>Filters</h2>
      <div class="form-grid">
        <select v-model="selectedCategory">
          <option value="all">All Events</option>
          <option value="member">Member / Loyalty</option>
          <option value="campaign">Campaigns / Coupons</option>
          <option value="order">Orders</option>
        </select>
        <input v-model="filterAction" placeholder="Action prefix filter" />
        <button class="btn" @click="loadEvents">Search</button>
      </div>
    </section>

    <section class="panel">
      <h2>Events ({{ events.length }})</h2>
      <table class="data-table" v-if="events.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>Action</th>
            <th>Resource</th>
            <th>Store</th>
            <th>Actor</th>
            <th>Time</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events" :key="event.id">
            <td>{{ event.id }}</td>
            <td>{{ event.action }}</td>
            <td>{{ event.resource_type }}:{{ event.resource_id }}</td>
            <td>{{ event.store_id ?? "—" }}</td>
            <td>{{ event.actor_user_id ?? "system" }}</td>
            <td>{{ formatTime(event.created_at) }}</td>
            <td class="detail-cell">{{ formatDetail(event.detail_json) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else>No audit events found for the current filters.</p>
    </section>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  listAuditEvents,
  listMemberAuditEvents,
  listCampaignAuditEvents,
  listOrderAuditEvents,
  type AuditEvent,
} from "@/services/audit";
import { notifyError } from "@/utils/feedback";

const events = ref<AuditEvent[]>([]);
const selectedCategory = ref("all");
const filterAction = ref("");
const errorMessage = ref("");

function formatTime(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function formatDetail(json: string): string {
  try {
    const obj = JSON.parse(json);
    return Object.entries(obj)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
  } catch {
    return json;
  }
}

async function loadEvents() {
  try {
    errorMessage.value = "";
    switch (selectedCategory.value) {
      case "member":
        events.value = await listMemberAuditEvents();
        break;
      case "campaign":
        events.value = await listCampaignAuditEvents();
        break;
      case "order":
        events.value = await listOrderAuditEvents();
        break;
      default:
        events.value = await listAuditEvents({
          action: filterAction.value || undefined,
          limit: 200,
        });
    }
  } catch (error) {
    errorMessage.value = notifyError(error, "Failed to load audit events.");
  }
}

onMounted(loadEvents);
</script>

<style scoped>
.detail-cell {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.85em;
  color: var(--color-text-muted, #666);
}
</style>
