require("dotenv").config();
const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const tripRoutes = require("./routes/tripRoutes");

const app = express();
app.use(cors());
app.use(express.json());

mongoose
  .connect(process.env.MONGODB_URI)
  .then(() => console.log("Mongo connected"))
  .catch((err) => console.error(err));

app.use("/api/trips", tripRoutes);

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Node server running on port ${PORT}`));
