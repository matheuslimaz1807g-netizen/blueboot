<template>
  <div class="min-h-screen bg-gray-50">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <!-- Product Image -->
      <div class="mb-8">
        <img
          :src="promotion.imageUrl"
          :alt="promotion.seoTitle"
          class="w-full h-96 object-cover rounded-lg shadow-lg"
        />
      </div>

      <!-- Title -->
      <h1 class="text-3xl font-bold text-gray-900 mb-4">
        {{ promotion.seoTitle }}
      </h1>

      <!-- Prices -->
      <div class="mb-6">
        <div class="flex items-center space-x-4">
          <span class="text-2xl font-semibold text-red-600 line-through">{{
            promotion.oldPrice
          }}</span>
          <span class="text-4xl font-bold text-green-600">{{
            promotion.newPrice
          }}</span>
        </div>
        <p v-if="promotion.couponCode" class="text-lg text-blue-600 mt-2">
          Código do Cupom: <strong>{{ promotion.couponCode }}</strong>
        </p>
      </div>

      <!-- Store -->
      <p class="text-lg text-gray-700 mb-4">
        Loja Parceira: <strong>{{ promotion.store }}</strong>
      </p>

      <!-- CTA Button -->
      <div class="mb-8">
        <a
          :href="promotion.telegramLink"
          target="_blank"
          class="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-lg text-xl shadow-lg transition duration-300"
        >
          PEGAR CUPOM E LINK
        </a>
      </div>

      <!-- Affiliate Link (optional, for direct purchase) -->
      <div v-if="promotion.affiliateLink" class="mb-8">
        <a
          :href="promotion.affiliateLink"
          target="_blank"
          class="text-blue-600 underline"
          >Link de Afiliado Direto</a
        >
      </div>

      <!-- Expiration -->
      <p v-if="promotion.expiresAt" class="text-sm text-gray-500">
        Oferta válida até:
        {{ new Date(promotion.expiresAt).toLocaleDateString("pt-BR") }}
      </p>
    </div>
  </div>
</template>

<script setup>
const route = useRoute();
const { slug } = route.params;

// Fetch promotion data on server-side
const { data: promotion } = await useFetch(`/api/promotions/${slug}`);

// Set SEO meta
useSeoMeta({
  title: `Oferta ${promotion.value?.couponCode || "Especial"} ${new Date().toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}`,
  description: `Aproveite esta oferta incrível: ${promotion.value?.seoTitle}. Preço antigo: ${promotion.value?.oldPrice}, Novo preço: ${promotion.value?.newPrice}. Use o cupom ${promotion.value?.couponCode} na loja ${promotion.value?.store}.`,
  ogTitle: promotion.value?.seoTitle,
  ogDescription: `Oferta especial com desconto. Novo preço: ${promotion.value?.newPrice}.`,
  ogImage: promotion.value?.imageUrl,
});

// Schema Markup for Rich Snippets
useHead({
  script: [
    {
      type: "application/ld+json",
      children: JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Product",
        name: promotion.value?.seoTitle,
        image: promotion.value?.imageUrl,
        offers: {
          "@type": "Offer",
          price: promotion.value?.newPrice
            ?.replace(/[^\d.,]/g, "")
            .replace(",", "."),
          priceCurrency: "BRL",
          availability: "https://schema.org/InStock",
          url: promotion.value?.affiliateLink,
          priceValidUntil: promotion.value?.expiresAt,
        },
        brand: {
          "@type": "Brand",
          name: promotion.value?.store,
        },
      }),
    },
  ],
});
</script>
