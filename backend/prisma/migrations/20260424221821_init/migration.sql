-- CreateTable
CREATE TABLE "Promotion" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "originalTitle" TEXT NOT NULL,
    "seoTitle" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "oldPrice" TEXT,
    "newPrice" TEXT NOT NULL,
    "couponCode" TEXT,
    "imageUrl" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "affiliateLink" TEXT NOT NULL,
    "telegramLink" TEXT NOT NULL,
    "expiresAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "Promotion_slug_key" ON "Promotion"("slug");
