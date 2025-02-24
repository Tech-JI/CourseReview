<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const course = ref(null)
const reviews = ref([])
const medians = ref([])
const difficultyVote = ref(null)
const qualityVote = ref(null)

const fetchCourse = async () => {
    const response = await axios.get(`/api/courses/${route.params.id}/`)
    course.value = response.data
}

const fetchReviews = async () => {
    const response = await axios.get(`/api/courses/${route.params.id}/reviews/`)
    reviews.value = response.data.results
}

const fetchMedians = async () => {
    const response = await axios.get(`/api/courses/${route.params.id}/medians/`)
    medians.value = response.data.medians
}

const handleVote = async (value, category) => {
    try {
        await axios.post(`/api/courses/${route.params.id}/vote/`, {
            value,
            category
        })
        await fetchCourse() // Refresh course data
    } catch (error) {
        console.error('Error voting:', error)
    }
}

onMounted(async () => {
    await fetchCourse()
    await fetchReviews()
    await fetchMedians()
})
</script>

<template>
    <div v-if="course" class="course-detail">
        <h1>{{ course.short_name }} | {{ course.course_title }}</h1>

        <div class="scores">
            <div class="score-box">
                <button @click="handleVote(1, 'quality')">👍</button>
                <h2>{{ course.quality_score }}</h2>
                <button @click="handleVote(-1, 'quality')">👎</button>
                <p>Quality Score</p>
            </div>

            <div class="score-box">
                <button @click="handleVote(1, 'difficulty')">👍</button>
                <h2>{{ course.difficulty_score }}</h2>
                <button @click="handleVote(-1, 'difficulty')">👎</button>
                <p>Difficulty Score</p>
            </div>
        </div>

        <div class="reviews">
            <h3>Reviews</h3>
            <div v-for="review in reviews" :key="review.id" class="review">
                <p><strong>{{ review.term }}</strong> with {{ review.professor }}:</p>
                <p>{{ review.comments }}</p>
            </div>
        </div>

        <div class="medians" v-if="medians.length">
            <h3>Medians</h3>
            <div class="median-chart">
                <!-- Add chart implementation here -->
            </div>
        </div>
    </div>
</template>

<style scoped>
.course-detail {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

.scores {
    display: flex;
    justify-content: space-around;
    margin: 20px 0;
}

.score-box {
    text-align: center;
}

.reviews {
    margin-top: 40px;
}

.review {
    margin: 20px 0;
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 4px;
}
</style>