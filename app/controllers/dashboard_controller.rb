class DashboardController < ApplicationController
  require 'httparty'
  require 'csv'
  require 'prawn'

  def index
    @filters = fetch_filter_options

    if params[:org_type]
      @selected = {
        org_type: params[:org_type],
        sy: params[:sy],
        grad_rate_type: params[:grad_rate_type],
        stu_grp: params[:stu_grp]
      }
      @data = fetch_filtered_data(@selected)
    else
      @selected = {}
      @data = []
    end
  end

  def download_csv
    data = fetch_filtered_data(params)
    csv_string = CSV.generate(headers: true) do |csv|
      csv << data.first.keys if data.any?
      data.each { |row| csv << row.values }
    end
    send_data csv_string, filename: "graduation_stats.csv"
  end

  def download_pdf
    data = fetch_filtered_data(params)
    pdf = Prawn::Document.new
    pdf.text "Graduation Stats Report", size: 14, align: :center
    pdf.move_down 10
    data.each_with_index do |row, i|
      pdf.text "#{i+1}. #{row.values.join(", ")}"
    end
    send_data pdf.render, filename: "graduation_stats.pdf", type: "application/pdf"
  end

  private

  def fetch_filter_options
    response = HTTParty.get("https://educationtocareer.data.mass.gov/resource/n2xa-p822.json?$limit=1000", headers: headers)
    df = response.parsed_response
    {
      org_types: df.map { |x| x["org_type"] }.compact.uniq.sort,
      school_years: df.map { |x| x["sy"] }.compact.uniq.sort.reverse,
      rate_types: df.map { |x| x["grad_rate_type"] }.compact.uniq.sort,
      student_groups: df.map { |x| x["stu_grp"] }.compact.uniq.sort
    }
  end

  def fetch_filtered_data(filters)
    where_clause = URI.encode_www_form_component("org_type='#{filters[:org_type]}' AND sy='#{filters[:sy]}' AND grad_rate_type='#{filters[:grad_rate_type]}' AND stu_grp='#{filters[:stu_grp]}'")
    url = "https://educationtocareer.data.mass.gov/resource/n2xa-p822.json?$where=#{where_clause}&$limit=50000"
    response = HTTParty.get(url, headers: headers)
    df = response.parsed_response

    numeric_cols = %w[cohort_cnt grad_pct in_sch_pct non_grad_pct ged_pct drpout_pct exclud_pct]
    df.each do |row|
      numeric_cols.each { |col| row[col] = row[col].to_f if row[col] }
    end

    name_col, code_col = case filters[:org_type]
                         when "District" then ["dist_name", "dist_code"]
                         when "School" then ["org_name", "org_code"]
                         else ["org_name", "org_code"]
                         end

    df.map.with_index(1) do |row, idx|
      {
        "S. No." => idx,
        name_col => row[name_col],
        code_col => row[code_col],
        "# in Cohort" => row["cohort_cnt"],
        "% Graduated" => row["grad_pct"],
        "% Still in School" => row["in_sch_pct"],
        "% Non-Grad Completers" => row["non_grad_pct"],
        "% H.S. Equiv." => row["ged_pct"],
        "% Dropped Out" => row["drpout_pct"],
        "% Permanently Excluded" => row["exclud_pct"]
      }
    end
  end

  def headers
    { "X-App-Token" => ENV["SOCRATA_APP_TOKEN"] }
  end
end