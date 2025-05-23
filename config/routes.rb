Rails.application.routes.draw do
  root "dashboard#index"
  get "/download_csv", to: "dashboard#download_csv"
  get "/download_pdf", to: "dashboard#download_pdf"
end