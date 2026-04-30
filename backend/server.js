import Fastify from "fastify";
import { PrismaClient } from "@prisma/client";

const fastify = Fastify({ logger: true });
const prisma = new PrismaClient();

// Function to generate slug from title
function generateSlug(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .substring(0, 100);
}

// POST /api/promotions
fastify.post("/api/promotions", async (request, reply) => {
  const {
    originalTitle,
    seoTitle,
    oldPrice,
    newPrice,
    couponCode,
    imageUrl,
    store,
    affiliateLink,
    telegramLink,
    expiresAt,
  } = request.body;

  // Generate unique slug
  let slug = generateSlug(seoTitle || originalTitle);
  let counter = 1;
  while (await prisma.promotion.findUnique({ where: { slug } })) {
    slug = `${generateSlug(seoTitle || originalTitle)}-${counter}`;
    counter++;
  }

  const promotion = await prisma.promotion.create({
    data: {
      originalTitle,
      seoTitle: seoTitle || originalTitle,
      slug,
      oldPrice,
      newPrice,
      couponCode,
      imageUrl,
      store,
      affiliateLink,
      telegramLink,
      expiresAt: expiresAt ? new Date(expiresAt) : null,
    },
  });

  reply.send(promotion);
});

// GET /api/promotions/:slug
fastify.get("/api/promotions/:slug", async (request, reply) => {
  const { slug } = request.params;

  const promotion = await prisma.promotion.findUnique({
    where: { slug },
  });

  if (!promotion) {
    reply.code(404).send({ error: "Promotion not found" });
    return;
  }

  reply.send(promotion);
});

// Run the server
const start = async () => {
  try {
    await fastify.listen({ port: 3000 });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
